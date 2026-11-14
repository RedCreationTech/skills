'use strict';

/*
 * Playwright overlay for evidence recordings.
 * The overlay is visual only: it never changes business data or fakes clicks.
 */

function injectOverlay(cfg) {
  if (window.__evidenceOverlayInstalled) {
    window.__evidenceOverlayCfg = cfg;
    return;
  }
  window.__evidenceOverlayInstalled = true;
  window.__evidenceOverlayCfg = cfg;

  const style = document.createElement('style');
  style.textContent = `
    #__ev_cursor, #__ev_label, #__ev_hint, #__ev_highlight {
      position: fixed; z-index: 2147483647; pointer-events: none;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    #__ev_cursor {
      width: 16px; height: 16px; left: 0; top: 0; border-radius: 50%;
      background: ${cfg.accent}; border: 3px solid #ffffff;
      box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.30), 0 2px 8px rgba(0,0,0,0.45);
      transform: translate(-100px, -100px); transition: transform 180ms ease-out;
    }
    #__ev_label {
      padding: 4px 8px; border-radius: 6px; background: rgba(8, 20, 34, 0.92);
      color: #f8fafc; font-size: 12px; line-height: 16px; max-width: 360px;
      transform: translate(-100px, -100px); opacity: 0; transition: opacity 120ms;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    #__ev_hint {
      left: 50%; bottom: 28px; transform: translateX(-50%);
      padding: 10px 16px; border-radius: 9px; background: rgba(8, 20, 34, 0.94);
      color: #f8fafc; font-size: 17px; line-height: 22px; max-width: 72vw;
      border: 1px solid rgba(34, 211, 238, 0.55); opacity: 0;
      transition: opacity 140ms; overflow: hidden; text-overflow: ellipsis;
      white-space: nowrap;
    }
    #__ev_highlight {
      border: 3px solid ${cfg.accent}; border-radius: 7px;
      background: rgba(34, 211, 238, 0.08); opacity: 0; transition: opacity 140ms;
    }
    #__ev_ripple {
      position: fixed; z-index: 2147483646; pointer-events: none; width: 18px;
      height: 18px; border-radius: 50%; border: 3px solid ${cfg.accent};
      transform: translate(-50%, -50%) scale(0.4); opacity: 0.9;
    }
  `;
  document.documentElement.appendChild(style);

  const cursor = document.createElement('div');
  cursor.id = '__ev_cursor';
  const label = document.createElement('div');
  label.id = '__ev_label';
  const hint = document.createElement('div');
  hint.id = '__ev_hint';
  const highlight = document.createElement('div');
  highlight.id = '__ev_highlight';
  document.documentElement.append(cursor, label, hint, highlight);

  let hintTimer = null;
  let highlightTimer = null;

  window.__evMove = (x, y) => {
    cursor.style.transform = `translate(${x - 8}px, ${y - 8}px)`;
    label.style.transform = `translate(${x + 14}px, ${y - 28}px)`;
  };

  window.__evRipple = (x, y) => {
    const r = document.createElement('div');
    r.id = '__ev_ripple';
    r.style.left = `${x}px`;
    r.style.top = `${y}px`;
    document.documentElement.appendChild(r);
    try {
      r.animate(
        [{ transform: 'translate(-50%, -50%) scale(0.4)', opacity: 0.95 },
         { transform: 'translate(-50%, -50%) scale(3.2)', opacity: 0 }],
        { duration: 520, easing: 'ease-out' }
      );
    } catch (_) {}
    setTimeout(() => r.remove(), 560);
  };

  window.__evHint = (text, ms) => {
    if (!cfg.showInput || !text) return;
    hint.textContent = text.length > 90 ? `${text.slice(0, 89)}…` : text;
    hint.style.opacity = '1';
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => { hint.style.opacity = '0'; }, ms || 1600);
  };

  window.__evHighlight = (rect, text, ms) => {
    highlight.style.left = `${rect.x}px`;
    highlight.style.top = `${rect.y}px`;
    highlight.style.width = `${rect.width}px`;
    highlight.style.height = `${rect.height}px`;
    highlight.style.opacity = '1';
    if (text) {
      label.textContent = text;
      label.style.opacity = '1';
    }
    clearTimeout(highlightTimer);
    highlightTimer = setTimeout(() => {
      highlight.style.opacity = '0';
      if (text) label.style.opacity = '0';
    }, ms || 1800);
  };
}

async function install(page, options = {}) {
  const cfg = {
    showInput: options.showInput !== false,
    accent: options.accent || '#22d3ee',
  };
  await page.addInitScript(injectOverlay, cfg);
  await page.evaluate(injectOverlay, cfg).catch(() => {});
}

function isSensitive(locator) {
  return locator.evaluate((el) => {
    if (!el || !el.getAttribute) return false;
    if (el.getAttribute('data-evidence-private') !== null) return true;
    if ((el.getAttribute('type') || '').toLowerCase() === 'password') return true;
    const text = [el.getAttribute('name'), el.getAttribute('id'),
      el.getAttribute('autocomplete'), el.getAttribute('aria-label')]
      .filter(Boolean).join(' ');
    return /(pass(word)?|pwd|secret|token|api[-_]?key|credential|card|phone|mobile|email)/i.test(text);
  }).catch(() => false);
}

async function click(locator, options = {}) {
  const page = locator.page();
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) throw new Error('Cannot click an element without a bounding box');
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await page.mouse.move(x, y, { steps: options.steps || 14 });
  await page.evaluate(({ x, y }) => window.__evRipple && window.__evRipple(x, y), { x, y });
  await page.waitForTimeout(options.pause === undefined ? 120 : options.pause);
  await page.mouse.click(x, y, {
    button: options.button || 'left',
    clickCount: options.clickCount || 1,
  });
  return locator;
}

async function type(locator, text, options = {}) {
  const page = locator.page();
  const privateField = options.private === true || await isSensitive(locator);
  const tag = await locator.evaluate((el) => (el.tagName || '').toLowerCase()).catch(() => '');
  const inputType = await locator.getAttribute('type').catch(() => null);

  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (box) {
    const x = box.x + Math.min(box.width / 2, 120);
    const y = box.y + box.height / 2;
    await page.mouse.move(x, y, { steps: 10 });
    await page.evaluate(({ x, y }) => window.__evRipple && window.__evRipple(x, y), { x, y });
  }

  if (tag === 'input' && inputType === 'file') {
    if (!options.files) throw new Error('File input requires options.files');
    await locator.setInputFiles(options.files);
  } else if (inputType && ['date', 'number', 'time', 'datetime-local', 'month', 'week'].includes(inputType)) {
    await locator.fill(String(text));
  } else {
    await locator.fill('');
    if (typeof locator.pressSequentially === 'function') {
      await locator.pressSequentially(String(text), { delay: options.delay || 35 });
    } else {
      await locator.type(String(text), { delay: options.delay || 35 });
    }
  }

  const shown = privateField ? '•'.repeat(Math.min(String(text).length, 12)) : String(text);
  await page.evaluate(({ shown }) => window.__evHint && window.__evHint(shown), { shown }).catch(() => {});
  return locator;
}

async function highlight(locator, text, duration = 1800) {
  const page = locator.page();
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) return;
  await page.evaluate(({ rect, text, duration }) => {
    if (window.__evHighlight) window.__evHighlight(rect, text, duration);
  }, { rect: box, text: text || '', duration }).catch(() => {});
}

async function moveTo(locator) {
  const page = locator.page();
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  if (!box) return;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 14 });
}

module.exports = { install, click, type, highlight, moveTo };