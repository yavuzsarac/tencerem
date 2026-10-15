const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const frontend=process.env.FRONTEND_URL||'http://127.0.0.1:3016';
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  await page.goto(frontend);
  await page.locator('#craving').fill('tavuklu pilav');await page.locator('#servings').fill('5');
  await page.getByRole('button',{name:'Tarifleri bul',exact:true}).click();
  await page.getByRole('heading',{name:/Bugün Tavuklu pilav ye\./}).waitFor();
  await page.getByRole('button',{name:'Bunu Yapacağım',exact:true}).click();
  await page.getByRole('button',{name:'Eksikleri Gör',exact:true}).click();
  for(const [id,name,amount] of [['chicken_breast','Tavuk göğsü','300'],['rice','Pirinç','500'],['salt','Tuz','10'],['olive_oil','Zeytinyağı','10']]){
   await page.getByLabel(`Evde var: ${name}`,{exact:true}).check();
   await page.locator(`#stock-${id}-quantity`).fill(amount);
  }
  await page.getByRole('button',{name:'Sepete Hazırla',exact:true}).click();
  await page.getByRole('heading',{name:'Sepetim',exact:true}).waitFor();
  const pricing=page.locator('.market-pricing');
  assert.match(await pricing.innerText(),/CANLI FİYAT DEĞİLDİR/);
  await pricing.getByRole('button',{name:'Marketleri Karşılaştır',exact:true}).click();
  await pricing.getByText('Demo sepet toplamı: 106,00 TL',{exact:true}).waitFor();
  assert.equal(await pricing.locator('.market-estimate').getAttribute('data-retailer'),'demo-b');
  await pricing.getByLabel('Demo Market Seç',{exact:true}).selectOption('demo-a');
  await pricing.getByText('Demo sepet toplamı: 110,00 TL',{exact:true}).waitFor();
  const chicken=pricing.locator('[data-market-ingredient="chicken_breast"]');
  assert.match(await chicken.innerText(),/300 g/);assert.match(await chicken.innerText(),/90,00 TL/);
  assert.match(await pricing.innerText(),/curated_demo/);assert.match(await pricing.innerText(),/2026-10-01/);
  await pricing.screenshot({path:'backend/.test-data/phase5-market-desktop.png'});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await pricing.screenshot({path:'backend/.test-data/phase5-market-mobile.png'});
  // Changing stock invalidates both basket and price state.
  await page.locator('#stock-salt-quantity').fill('0');
  assert.equal(await page.locator('.market-estimate').count(),0);
  await page.getByRole('button',{name:'Sepete Hazırla',exact:true}).click();
  await page.getByRole('heading',{name:'Sepetim',exact:true}).waitFor();
  await pricing.getByRole('button',{name:'Marketleri Karşılaştır',exact:true}).click();
  await pricing.getByText(/Hiçbir demo market/).waitFor();
  assert.match(await pricing.innerText(),/kaşık\/bardak dönüşümü yapılmaz/);
  assert.equal(await pricing.getByText(/Demo sepet toplamı:/).count(),0);
  // Browser-facing proxy failure remains retryable, with no invented result.
  await page.route('**/api/baskets/compare',route=>route.fulfill({status:502,body:'{}',contentType:'application/json'}));
  await pricing.getByRole('button',{name:'Marketleri Karşılaştır',exact:true}).click();
  await pricing.getByRole('alert').waitFor();assert.equal(await pricing.locator('.market-estimate').count(),0);
  await page.unroute('**/api/baskets/compare');
  await pricing.getByRole('button',{name:'Marketleri Karşılaştır',exact:true}).click();
  await pricing.getByText(/Hiçbir demo market/).waitFor();
  console.log('PASS: demo pricing browser; pantry, best complete market, alternatives, TRY formatting, provenance, partial warnings, reset, mobile, error/retry');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
