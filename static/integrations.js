(() => {
  'use strict';
  const config=document.getElementById('platform-client');
  if(!config || !window.CookieConsent) return;
  const loaded=new Set();
  function script(key,src,attrs={}) {
    if(loaded.has(key)) return; loaded.add(key);
    const element=document.createElement('script');element.src=src;element.async=true;
    element.nonce=config.nonce;
    Object.entries(attrs).forEach(([k,v])=>element.setAttribute(k,v));
    document.head.appendChild(element);return element;
  }
  function apply() {
    const analytics=CookieConsent.acceptedCategory('analytics');
    const advertising=CookieConsent.acceptedCategory('advertising');
    if(analytics && config.dataset.umamiUrl && config.dataset.umamiId)
      script('umami',config.dataset.umamiUrl,{'data-website-id':config.dataset.umamiId});
    if(config.dataset.gtm && (analytics || advertising)) {
      window.dataLayer=window.dataLayer||[];
      function gtag(){window.dataLayer.push(arguments);}
      gtag('consent','default',{analytics_storage:'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'});
      gtag('consent','update',{analytics_storage:analytics?'granted':'denied',ad_storage:advertising?'granted':'denied',ad_user_data:advertising?'granted':'denied',ad_personalization:advertising?'granted':'denied'});
      if(!loaded.has('gtm')) window.dataLayer.push({'gtm.start':Date.now(),event:'gtm.js'});
      script('gtm','https://www.googletagmanager.com/gtm.js?id='+encodeURIComponent(config.dataset.gtm));
    }
    if(advertising && config.dataset.adsense && document.querySelector('ins.adsbygoogle')) {
      const ad=script('ads','https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='+encodeURIComponent(config.dataset.adsense),{crossorigin:'anonymous'});
      if(ad) ad.addEventListener('load',()=>script('ads-init',config.dataset.adsInit));
    }
  }
  CookieConsent.run({
    onConsent:apply,
    onChange:()=>location.reload(),
    categories:{necessary:{enabled:true,readOnly:true},analytics:{},advertising:{}},
    language:{default:'en',translations:{en:{
      consentModal:{title:'Your privacy choices',description:'Choose whether Cedarmond TV may load optional analytics and advertising. You can change this at any time.',acceptAllBtn:'Accept all',acceptNecessaryBtn:'Essential only',showPreferencesBtn:'Choose settings'},
      preferencesModal:{title:'Privacy choices',acceptAllBtn:'Accept all',acceptNecessaryBtn:'Essential only',savePreferencesBtn:'Save choices',closeIconLabel:'Close',sections:[
        {title:'Essential',description:'Security and your saved preferences.',linkedCategory:'necessary'},
        {title:'Analytics',description:'Optional audience measurement.',linkedCategory:'analytics'},
        {title:'Advertising',description:'Optional advertising services.',linkedCategory:'advertising'}
      ]}
    }}}
  });
  const button=document.getElementById('news-alerts');
  if(!button) return;
  const status=document.getElementById('alerts-status');
  if(!('serviceWorker' in navigator) || !('PushManager' in window)) {button.hidden=true;return;}
  const csrf=document.querySelector('#platform-csrf [name=csrfmiddlewaretoken]').value;
  const b64=value=>Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-value.length%4)%4)),c=>c.charCodeAt(0));
  button.addEventListener('click',async()=>{
    button.disabled=true;
    try {
      const registration=await navigator.serviceWorker.register('/webpush-worker.js');
      let sub=await registration.pushManager.getSubscription();
      const deleting=!!sub;
      if(!sub) sub=await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64(config.dataset.pushKey)});
      const data=sub.toJSON(); if(deleting) data.action='delete';
      const response=await fetch('/push/subscription/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf,'X-Subscription-Token':localStorage.getItem('cedarmond-push-token')||''},body:JSON.stringify(data)});
      if(!response.ok) throw new Error('Unable to update alerts. Check browser notification settings.');
      const result=await response.json();
      if(deleting) {await sub.unsubscribe();localStorage.removeItem('cedarmond-push-token');}
      else localStorage.setItem('cedarmond-push-token',result.token);
      button.textContent=deleting?'Enable news alerts':'Disable news alerts';status.textContent=deleting?'Alerts disabled.':'Alerts enabled.';
    } catch(error) {status.textContent=error.message;}
    finally {button.disabled=false;}
  });
  navigator.serviceWorker.getRegistration('/').then(async r=>{if(r && await r.pushManager.getSubscription()) button.textContent='Disable news alerts';});
})();
