/**
 * Hermes Web Fetcher - Universal Content Extraction
 * 
 * Uses chrome.scripting.executeScript to inject into any webpage
 * Reuses user's logged-in cookies, avoids CDP ban risk
 * 
 * Inspired by Accio's extract-readability.js
 */

/**
 * Fetch list items from a page (collections, search results, etc.)
 */
export async function fetchList(tabId, options = {}) {
  const {
    itemSelector = '[data-zop-question], [data-zop], .CollectionItem, .ContentItem, article, .post',
    titleSelector = 'h2, h3, .ContentItem-title, a[data-zop-question], .title',
    linkSelector = 'a[href*="/question/"], a[href*="/p/"], a.article-link, a.post-link, a[href]',
    authorSelector = '.UserLink-link, .ContentItem-actions a[href*="/people/"], .author, .byline',
    dateSelector = 'time, .ContentItem-meta time, .date, .published',
    idPattern = '/p/(\\d+)|/question/(\\d+)|/article/(\\d+)',
    maxItems = 100
  } = options;
  
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: (selectors, idPattern, maxItems) => {
      const items = [];
      const elements = document.querySelectorAll(selectors.itemSelector);
      
      elements.forEach((item, index) => {
        if (items.length >= maxItems) return;
        
        const titleEl = item.querySelector(selectors.titleSelector);
        const linkEl = item.querySelector(selectors.linkSelector);
        const authorEl = item.querySelector(selectors.authorSelector);
        const dateEl = item.querySelector(selectors.dateSelector);
        
        if (titleEl && linkEl) {
          const url = linkEl.href.split('?')[0];
          const idMatch = url.match(new RegExp(idPattern));
          const articleId = idMatch ? (idMatch[1] || idMatch[2] || idMatch[3]) : 'unknown';
          
          items.push({
            index: index,
            title: titleEl.textContent.trim(),
            url: url,
            id: articleId,
            author: authorEl ? authorEl.textContent.trim() : '',
            date: dateEl ? dateEl.getAttribute('datetime') || dateEl.textContent.trim() : ''
          });
        }
      });
      
      // Try to get pagination info
      const pagination = document.querySelector('.Pagination, .pagination, .pager, [role="navigation"]');
      let pageInfo = { currentPage: 1, totalPages: 1 };
      
      if (pagination) {
        const pages = Array.from(pagination.querySelectorAll('button, a, span'))
          .map(el => el.textContent).filter(t => /^\d+$/.test(t.trim()));
        if (pages.length > 0) {
          pageInfo.totalPages = Math.max(...pages.map(Number));
        }
        
        const activePage = pagination.querySelector('.active, [aria-current="page"], button[disabled]');
        if (activePage && /^\d+$/.test(activePage.textContent.trim())) {
          pageInfo.currentPage = parseInt(activePage.textContent.trim());
        }
      }
      
      // Also try URL params
      const urlParams = new URLSearchParams(window.location.search);
      const pageParam = urlParams.get('page');
      if (pageParam && /^\d+$/.test(pageParam)) {
        pageInfo.currentPage = parseInt(pageParam);
      }
      
      return {
        items,
        pageInfo,
        totalItems: items.length,
        url: window.location.href
      };
    },
    args: [{
      itemSelector,
      titleSelector,
      linkSelector,
      authorSelector,
      dateSelector
    }, idPattern, maxItems]
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Fetch full article content from a page
 * Dual-path extraction: Simple walker + Scoring-based (like Accio)
 */
export async function fetchArticle(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => {
      // Get title
      const title = document.querySelector('h1')?.textContent?.trim() || 
                   document.querySelector('meta[property="og:title"]')?.content ||
                   document.title.split('-')[0].trim() || '';
      
      // Path 1: Simple DOM walker (like Accio's simpleExtract)
      function simpleExtract() {
        const main = document.querySelector('main, article, [role="main"], #content, .content, .Post-RichText, .RichText')
        const root = main || document.body
        
        const lines = []
        const walk = (node) => {
          if (node.nodeType === 3) {
            const t = node.textContent.replace(/\s+/g, ' ').trim()
            if (t) lines.push(t)
            return
          }
          if (node.nodeType !== 1) return
          
          const tag = node.tagName
          try {
            const style = getComputedStyle(node)
            if (style.display === 'none' || style.visibility === 'hidden') return
          } catch { /* skip */ }
          
          if (/^H[1-6]$/.test(tag)) {
            lines.push('\n' + '#'.repeat(+tag[1]) + ' ' + node.textContent.trim())
          } else if (tag === 'P') {
            lines.push('\n' + node.innerText.replace(/\s+/g, ' ').trim())
          } else if (tag === 'LI') {
            lines.push('- ' + node.innerText.replace(/\s+/g, ' ').trim())
          } else if (tag === 'A' && node.href) {
            lines.push(`[${node.textContent.trim()}](${node.href})`)
          } else if (tag === 'IMG' && node.alt) {
            lines.push(`![${node.alt}](${node.src})`)
          } else if (tag === 'PRE' || tag === 'CODE') {
            lines.push('\n```\n' + node.textContent.trim() + '\n```')
          } else if (tag === 'BR') {
            lines.push('\n')
          } else if (tag === 'TABLE') {
            lines.push('\n' + node.innerText.replace(/\t/g, ' | ').trim())
          } else {
            for (const child of node.childNodes) walk(child)
            if (node.shadowRoot) for (const child of node.shadowRoot.childNodes) walk(child)
          }
        }
        
        walk(root)
        return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim()
      }
      
      // Path 2: Scoring-based extraction (like Accio's scoringExtract)
      function scoringExtract() {
        const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'NAV', 'FOOTER', 'HEADER', 'ASIDE', 'FORM'])
        const candidates = []
        
        function score(el) {
          if (SKIP.has(el.tagName)) return 0
          const text = el.innerText || ''
          const textLen = text.length
          if (textLen < 25) return 0
          
          let s = 0
          const paragraphs = el.querySelectorAll('p')
          s += paragraphs.length * 3
          s += Math.min(textLen / 100, 30)
          
          const links = el.querySelectorAll('a')
          const linkText = [...links].reduce((sum, a) => sum + (a.textContent || '').length, 0)
          const linkDensity = textLen > 0 ? linkText / textLen : 1
          if (linkDensity > 0.5) s *= 0.3
          
          const commas = (text.match(/[,,.]/g) || []).length
          s += commas
          
          if (el.id?.match(/article|content|main|post|body/i)) s *= 1.5
          if (el.className?.match(/article|content|main|post|body/i)) s *= 1.3
          if (el.className?.match(/sidebar|comment|footer|nav|menu|ad|banner/i)) s *= 0.3
          
          return s
        }
        
        for (const el of document.querySelectorAll('div, section, article, main')) {
          const s = score(el)
          if (s > 0) candidates.push({ el, score: s })
        }
        
        candidates.sort((a, b) => b.score - a.score)
        const best = candidates[0]
        if (!best || best.score < 10) return ''
        
        const text = best.el.innerText || ''
        return text.replace(/\t/g, ' ').replace(/ {2,}/g, ' ').replace(/\n{3,}/g, '\n\n').trim()
      }
      
      const simple = simpleExtract()
      const scored = scoringExtract()
      
      // Pick the longer result
      let content
      if (simple.length >= scored.length || simple.length > 800) {
        content = simple
      } else {
        content = scored
      }
      
      // Fallback to body if both are too short
      if (content.length < 200) {
        const fallback = (document.body?.innerText || '')
          .replace(/\t/g, ' ').replace(/ {2,}/g, ' ').replace(/\n{3,}/g, '\n\n').trim()
        if (fallback.length > content.length) content = fallback
      }
      
      // Get metadata
      const author = document.querySelector('.UserLink-link, .AuthorInfo-name, .Post-Author, .author, .byline, meta[name="author"]')?.textContent?.trim() || 
                    document.querySelector('meta[property="article:author"]')?.content || ''
      
      const dateEl = document.querySelector('time, .date, .published, meta[property="article:published_time"]')
      const date = dateEl ? (dateEl.getAttribute('datetime') || dateEl.getAttribute('content') || dateEl.textContent.trim()) : ''
      
      return {
        title,
        content: content.slice(0, 50000),
        author: author.slice(0, 200),
        date: date.slice(0, 20),
        url: window.location.href,
        method: content === simple ? 'walker' : content.length < 200 ? 'body-fallback' : 'scoring'
      }
    }
  });
  
  return results[0]?.result || { error: 'No result' };
}

/**
 * Navigate to a URL and wait for page load
 */
export async function navigateToUrl(tabId, url) {
  await chrome.tabs.update(tabId, { url });
  
  // Wait for page load
  return new Promise((resolve) => {
    const checkLoaded = () => {
      chrome.tabs.get(tabId, (tab) => {
        if (tab.status === 'complete') {
          setTimeout(() => resolve(tab), 2000); // Extra delay for JS rendering
        } else {
          setTimeout(checkLoaded, 500);
        }
      });
    };
    checkLoaded();
  });
}

/**
 * Get current page info
 */
export async function getPageInfo(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    func: () => ({
      title: document.title,
      url: window.location.href,
      isReady: document.readyState === 'complete'
    })
  });
  
  return results[0]?.result || { error: 'No result' };
}
