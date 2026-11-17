const fs=require('node:fs');
const root='static/vendor/cookieconsent';fs.mkdirSync(root,{recursive:true});
for(const file of ['cookieconsent.umd.js','cookieconsent.css']) fs.copyFileSync('node_modules/vanilla-cookieconsent/dist/'+file,root+'/'+file);
fs.copyFileSync('node_modules/vanilla-cookieconsent/LICENSE',root+'/LICENSE');
