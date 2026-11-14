/* Visual-only Playwright helpers. Use only with non-sensitive demo data. */
async function install(page, {showInput = false} = {}) {
  await page.addInitScript(({showInput}) => {
    const add = () => {
      if (document.querySelector('#evidence-cursor')) return;
      const style = document.createElement('style');
      style.textContent = `#evidence-cursor{position:fixed;z-index:2147483647;pointer-events:none;display:none;filter:drop-shadow(0 1px 2px #0008)}#evidence-cursor b{position:absolute;left:-13px;top:-13px;width:30px;height:30px;border:2px solid #18a999;border-radius:50%;opacity:0}#evidence-cursor.pressed b{animation:evidence-ring .5s ease-out}@keyframes evidence-ring{0%{opacity:1;transform:scale(.35)}100%{opacity:0;transform:scale(1.5)}}#evidence-input{position:fixed;right:24px;top:70px;z-index:2147483646;pointer-events:none;display:none;max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding:9px 14px;border-radius:7px;background:#102c39;color:#b3fff1;font:15px sans-serif}`;
      const cursor = document.createElement('div'); cursor.id = 'evidence-cursor';
      cursor.innerHTML = '<b></b><svg width="22" height="28" viewBox="0 0 22 28"><path d="M2 1L2 22L8 17L11 25L15 23L12 16L20 15Z" fill="white" stroke="#102030" stroke-width="1.5"/></svg>';
      const input = document.createElement('div'); input.id = 'evidence-input';
      document.head.appendChild(style); document.body.append(cursor, input);
      document.addEventListener('mousemove', e => {cursor.style.display='block';cursor.style.transform=`translate(${e.clientX}px,${e.clientY}px)`;}, true);
      document.addEventListener('mousedown', () => {cursor.classList.remove('pressed');void cursor.offsetWidth;cursor.classList.add('pressed');}, true);
      if (showInput) document.addEventListener('input', e => {
        const el=e.target, kind=(el.type||'').toLowerCase(), name=[el.name,el.id,el.autocomplete].join(' ').toLowerCase();
        if (!['INPUT','TEXTAREA'].includes(el.tagName) || el.closest('[data-evidence-private]') || /password|token|secret|api.?key|card|phone|email/.test(name) || ['password','email','tel','file'].includes(kind)) {input.style.display='none';return;}
        input.textContent='正在输入  '+String(el.value||'').slice(0,120);input.style.display='block';clearTimeout(window.__evidenceInputTimer);window.__evidenceInputTimer=setTimeout(()=>input.style.display='none',1500);
      }, true);
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',add,{once:true}); else add();
  }, {showInput});
}
async function type(locator, value, delay = 65) {
  const type = (await locator.getAttribute('type') || '').toLowerCase();
  if (type === 'file') return locator.setInputFiles(value);
  if (['date','datetime-local','number','time','password'].includes(type)) return locator.fill(value);
  await locator.click(); await locator.fill(''); await locator.pressSequentially(String(value), {delay});
  if (await locator.inputValue() !== String(value)) throw new Error('Input did not retain the expected value');
}
module.exports = {install, type};
