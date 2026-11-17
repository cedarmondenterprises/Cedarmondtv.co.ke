self.addEventListener('push', event => {
  let data; try { data=event.data.json(); } catch (_) { return; }
  let target; try { target=new URL(data.url,self.location.origin); } catch (_) { return; }
  if(target.origin!==self.location.origin) return;
  event.waitUntil(self.registration.showNotification(data.title || 'Cedarmond TV', {
    body:data.body || '', tag:data.tag || 'cedarmond-news', data:{url:target.href}
  }));
});
self.addEventListener('notificationclick', event => {
  event.notification.close();
  const target=new URL(event.notification.data.url,self.location.origin);
  if(target.origin===self.location.origin) event.waitUntil(clients.openWindow(target.href));
});
