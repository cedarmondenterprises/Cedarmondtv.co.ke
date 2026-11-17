const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir:'./tests/browser', workers:1,
  use:{launchOptions: process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {},baseURL:'http://127.0.0.1:18081',viewport:{width:390,height:844}},
  webServer:{command:(process.env.TEST_PYTHON || 'python')+' manage.py runserver 127.0.0.1:18081 --noreload',url:'http://127.0.0.1:18081/healthz/',reuseExistingServer:false,env:{DEBUG:'1',UMAMI_SCRIPT_URL:'https://analytics.example.test/script.js',UMAMI_WEBSITE_ID:'test-site'}},
});
