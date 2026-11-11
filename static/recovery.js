(() => {
  const editors = new Map();
  document.addEventListener('prose-editor:ready', event => {
    editors.set(event.detail.textarea.name, event.detail.editor);
    event.detail.editor.on('update', () => event.detail.textarea.dispatchEvent(new Event('input', {bubbles:true})));
  });
  document.addEventListener('DOMContentLoaded', async () => {
    const panel = document.querySelector('#draft-recovery');
    if (!panel) return;
    const form = panel.closest('form'), status = panel.querySelector('#recovery-status'), recover = panel.querySelector('#recover-copy');
    const names = ['title','slug','summary','body','seo_title','seo_description','category','author','media_asset','tags'];
    let version = 0, busy = false, dirty = false, blocked = false, timer, snapshot = null;
    const recoveryInput = form.querySelector('[name=recovery_key]');
    if (recoveryInput) recoveryInput.value = panel.dataset.key;
    const base = form.querySelector('[name=loaded_version]')?.value || '';
    const values = () => Object.fromEntries(names.map(name => {
      const field = form.elements.namedItem(name);
      if (name === 'tags') {
        const chosen=document.getElementById('id_tags_to');
        return [name, Array.from(chosen?.options || field?.options || []).map(option=>option.value)];
      }
      return [name, editors.has(name) ? editors.get(name).getHTML() : (field?.value || '')];
    }));
    const save = async () => {
      if (!dirty || busy || blocked) return;
      busy = true; dirty = false; status.textContent = 'Saving private recovery copy…';
      try {
        const response = await fetch(panel.dataset.url,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':form.elements.csrfmiddlewaretoken.value},body:JSON.stringify({version,article_id:panel.dataset.article ? Number(panel.dataset.article) : null,base_updated_at:base,data:values()})});
        const result = await response.json();
        if (!response.ok) { blocked = response.status === 409 || response.status === 403; throw new Error(result.error || 'Recovery could not be saved.'); }
        version=result.version;status.textContent='Recovery saved at '+new Date(result.saved_at).toLocaleTimeString()+'. Not published.';
      } catch(error) { dirty=true;status.textContent=error.message+' Keep this page open or copy your writing before reloading.'; }
      finally {busy=false;}
    };
    try {
      const response = await fetch(panel.dataset.url,{credentials:'same-origin'});
      if (!response.ok) throw new Error('Recovery is unavailable for this article.');
      const result = await response.json();version=result.version;
      if (result.exists) {snapshot=result.data;recover.hidden=false;status.textContent='A recovery copy from '+new Date(result.saved_at).toLocaleString()+' is available. Review it before saving.';}
      else status.textContent='Changes will be saved privately as you write.';
    } catch(error) {blocked=true;status.textContent=error.message+' Use the normal Save button.';}
    recover.addEventListener('click', () => {
      if (!snapshot) return;
      for (const [name,value] of Object.entries(snapshot)) {
        const field=form.elements.namedItem(name); if (!field) continue;
        if (name==='tags') {
          // Django's filtered multi-select uses two lists; update its selected side as well.
          if (window.SelectBox && document.getElementById('id_tags_to')) {
            const from=document.getElementById('id_tags_from'), to=document.getElementById('id_tags_to');
            for (const option of [...from.options,...to.options]) {
              if(value.includes(option.value)) to.add(option); else from.add(option);
            }
          } else for (const option of field.options) option.selected=value.includes(option.value);
        } else if(editors.has(name)) editors.get(name).commands.setContent(value);
        else field.value=value;
      }
      recover.hidden=true;dirty=true;status.textContent='Recovered into this form. Review the content, then Save.';
    });
    form.addEventListener('input',()=>{dirty=true;clearTimeout(timer);timer=setTimeout(save,3000);});
    form.addEventListener('change',()=>{dirty=true;clearTimeout(timer);timer=setTimeout(save,3000);});
    setInterval(save,15000);
    form.addEventListener('submit',()=>{blocked=true;});
    window.addEventListener('beforeunload',event=>{if((dirty||busy)&&!blocked){event.preventDefault();event.returnValue='';}});
  });
})();
