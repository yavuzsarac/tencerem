const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const frontend=process.env.FRONTEND_URL||'http://127.0.0.1:3014';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  await page.goto(frontend);
  const panel=page.locator('.assistant-panel');
  await panel.getByLabel('Bugün nasıl bir şey yemek istiyorsun?',{exact:true}).fill('Evde tavuk var, 30 dakikadan uzun sürmesin ve proteinli olsun.');
  await panel.getByRole('button',{name:'Tencerem Öner',exact:true}).click();
  await panel.getByRole('heading',{name:/Bugün .* ye\./}).waitFor();
  await panel.getByText(/Katalog sıralamasıyla öneri/).waitFor();
  const first=await panel.locator('#primary-meal-heading').textContent();
  await panel.getByRole('button',{name:'Başka Öner',exact:true}).click();
  await page.waitForFunction(old=>document.querySelector('.assistant-panel #primary-meal-heading')?.textContent!==old,first);
  await panel.getByLabel('İsteğini nasıl değiştirelim?',{exact:true}).fill('Bunu 4 kişilik yapacağım.');
  await panel.getByRole('button',{name:'Öneriyi Güncelle',exact:true}).click();
  await panel.getByText(/4 kişilik/).first().waitFor();
  await panel.getByRole('button',{name:'Bunu Yapacağım',exact:true}).click();
  await panel.getByRole('button',{name:'Eksikleri Gör',exact:true}).click();
  await panel.getByRole('button',{name:'Sepete Hazırla',exact:true}).click();
  await panel.getByRole('heading',{name:'Sepetim',exact:true}).waitFor();
  assert(!/Migros|Carrefour|Getir|₺\s*\d/.test(await panel.innerText()));
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:'backend/.test-data/phase4-assistant-mobile.png',fullPage:true});
  await panel.getByRole('button',{name:'Yeni Karar',exact:true}).click();
  await panel.getByLabel('Bugün nasıl bir şey yemek istiyorsun?',{exact:true}).fill('10 dakikada fırında tavuk yap');
  await panel.getByRole('button',{name:'Tencerem Öner',exact:true}).click();
  await panel.getByRole('heading',{name:'Uygun yemek bulunamadı',exact:true}).waitFor();
  console.log('PASS: anonymous assistant fallback, one meal, next, refinement, acceptance, basket, conflict, mobile; no live AI');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
