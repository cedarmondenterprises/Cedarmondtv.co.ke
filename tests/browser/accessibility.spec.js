const { test, expect } = require('@playwright/test');
const AxeBuilder=require('@axe-core/playwright').default;
for(const path of ['/','/search/','/contact/','/admin/login/']) {
  test('accessible mobile page '+path,async({page})=>{
    await page.goto(path);
    const report=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa','wcag22aa']).analyze();
    expect(report.violations).toEqual([]);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  });
}
test('optional analytics waits for consent',async({page})=>{
  const requests=[];
  await page.route('https://analytics.example.test/**',route=>{requests.push(route.request().url());return route.fulfill({body:'',contentType:'application/javascript'});});
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Essential only',exact:true}).first()).toBeVisible();
  expect(requests).toHaveLength(0);
  await page.getByRole('button',{name:'Essential only',exact:true}).first().click();
  expect(requests).toHaveLength(0);
  await page.getByRole('button',{name:'Privacy choices',exact:true}).click();
  await page.getByRole('button',{name:'Accept all',exact:true}).last().click();
  await expect.poll(()=>requests.length).toBe(1);
});
