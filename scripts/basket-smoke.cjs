const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const screenshots=process.env.SCREENSHOT_PREFIX || 'phase2';
const frontend=process.env.FRONTEND_URL || 'http://127.0.0.1:3000';
const backend=process.env.TEST_BACKEND_URL || 'http://127.0.0.1:8000';
async function post(path,body,base=backend) {
 const response=await fetch(`${base}${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 assert.equal(response.status,200); return response.json();
}
(async()=>{
 assert.equal((await fetch(`${backend}/health`)).status,200);
 const recipes=await (await fetch(`${backend}/api/v1/recipes`)).json();
 assert.equal(recipes.length,24);
 const detail=await (await fetch(`${backend}/api/v1/recipes/tavuklu-pilav?servings=6`)).json();
 assert.equal(Number(detail.scaled_ingredients[0].quantity),600);
 const preferences={craving:'tavuk',servings:5,max_prep_minutes:30,dietary_preference:'none',pantry:'tavuk, pirinç, tuz'};
 const ranked=await post('/api/v1/recipes/recommend',preferences);
 assert.ok(ranked.recipes.length>1);
 assert.ok(ranked.recipes.every(r=>r.recipe.total_minutes<=30));
 const receipt=await post('/api/meal-preferences',{...preferences,pantry:undefined,max_budget_try:'350'},frontend);
 assert.equal(receipt.mode,'development');
 // Live multi-recipe test: independent servings require 300g chicken each.
 const multi=await post('/api/v1/baskets/preview',{
  recipes:[{slug:'tavuklu-pilav',servings:3},{slug:'tavuk-sote',servings:2}],
  pantry:[{ingredient_id:'chicken_breast',quantity:'0.4',unit:'kg'}],optional_policy:'required_only'});
 const chicken=multi.items.find(i=>i.ingredient_id==='chicken_breast').components[0];
 assert.equal(Number(chicken.required_quantity),600);
 assert.equal(Number(chicken.pantry_allocated_quantity),400);
 assert.equal(Number(chicken.missing_quantity),200);
 assert.equal(chicken.contributions.length,2);
 const browser=await chromium.launch({headless:true,channel:'msedge'});
 try {
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  await page.goto(frontend);
  assert.equal(await page.locator('html').getAttribute('lang'),'tr');
  await page.keyboard.press('Tab'); assert.equal(await page.locator(':focus').innerText(),'Forma geç');
  const submit=page.getByRole('button',{name:'Tarifleri bul',exact:true});
  await submit.click(); assert.equal(await page.locator('#craving').evaluate(el=>el.validity.valueMissing),true);
  await page.locator('#craving').fill('tavuk'); await page.locator('#servings').fill('0');
  await submit.click(); assert.equal(await page.locator('#servings').evaluate(el=>el.validity.rangeUnderflow),true);
  await page.locator('#servings').fill('5'); await page.locator('#pantry').fill('tavuk, pirinç, tuz');
  await submit.click(); await page.locator('#primary-meal-heading').waitFor();
  assert.equal(await page.locator('.recipe-card').count(),1);
  const first=await page.locator('#primary-meal-heading').innerText();
  await page.getByRole('button',{name:'Başka Öner',exact:true}).click();
  assert.notEqual(await page.locator('#primary-meal-heading').innerText(),first);
  for(let n=0;n<10 && !(await page.locator('#primary-meal-heading').innerText()).includes('Tavuklu pilav');n++)
   await page.getByRole('button',{name:'Başka Öner',exact:true}).click();
  assert.match(await page.locator('#primary-meal-heading').innerText(),/Tavuklu pilav/);
  await page.screenshot({path:`docs/${screenshots}-recommendation.png`,fullPage:true});
  await page.getByRole('button',{name:'Bunu Yapacağım',exact:true}).click();
  assert.equal(await page.locator('.instructions li').count(),3);
  await page.getByRole('button',{name:'Eksikleri Gör',exact:true}).click();
  await page.getByLabel('Evdeki miktar: Tavuk göğsü',{exact:true}).fill('0.3');
  await page.getByLabel('Birim: Tavuk göğsü',{exact:true}).selectOption('kg');
  await page.getByLabel('Evdeki miktar: Pirinç',{exact:true}).fill('500');
  const prepare=page.getByRole('button',{name:'Sepete Hazırla',exact:true});
  // Make the loading state observable while retaining the actual backend request.
  let release,arrived;
  const gate=new Promise(resolve=>{release=resolve});
  const intercepted=new Promise(resolve=>{arrived=resolve});
  const hold=async route=>{arrived();await gate;await route.continue()};
  await page.route('**/api/baskets/preview',hold);
  await prepare.click(); await intercepted;
  assert.equal(await page.getByRole('button',{name:'Sepet hesaplanıyor…'}).isDisabled(),true);
  release(); await page.getByRole('heading',{name:'Sepetim',exact:true}).waitFor();
  await page.unroute('**/api/baskets/preview',hold);
  const basket=page.locator('.basket-preview');
  const chickenItem=basket.locator('[data-ingredient="chicken_breast"]');
  assert.match(await chickenItem.innerText(),/500 g/);assert.match(await chickenItem.innerText(),/300 g/);assert.match(await chickenItem.innerText(),/200 g/);
  assert.match(await basket.locator('[data-ingredient="rice"]').innerText(),/Evde yeterli/);
  assert.match(await basket.locator('[data-ingredient="salt"]').innerText(),/Evde var · miktar bilinmiyor/);
  assert.equal(await basket.locator('[data-ingredient="yogurt"]').count(),0);
  assert.doesNotMatch(await basket.innerText(),/[₺$€]/);
  const check=chickenItem.getByRole('checkbox');await check.check();assert.equal(await check.isChecked(),true);
  await chickenItem.locator('summary').click();assert.match(await chickenItem.innerText(),/Tarif katkıları toplamı/);
  await basket.screenshot({path:`docs/${screenshots}-basket.png`});
  await page.setViewportSize({width:375,height:812});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  await basket.screenshot({path:`docs/${screenshots}-mobile-basket.png`});
  await page.getByLabel('İsteğe bağlı malzemeleri dahil et',{exact:true}).check();
  assert.equal(await page.locator('.basket-preview').count(),0);
  await prepare.click();await page.getByRole('heading',{name:'Sepetim',exact:true}).waitFor();
  assert.equal(await basket.locator('[data-ingredient="yogurt"]').count(),1);
  assert.equal(await basket.locator('[data-ingredient="chicken_breast"]').getByRole('checkbox').isChecked(),false);
  // An incompatible pantry unit must be shown, not subtracted as grams.
  await page.getByLabel('Evdeki miktar: Pirinç',{exact:true}).fill('1');
  await page.getByLabel('Birim: Pirinç',{exact:true}).selectOption('cup');
  await prepare.click();await page.getByRole('heading',{name:'Sepetim',exact:true}).waitFor();
  assert.match(await basket.locator('[data-ingredient="rice"]').innerText(),/Uyumsuz birimler/);
  assert.match(await basket.locator('[data-ingredient="rice"]').innerText(),/1 su bardağı/);
  const fail=route=>route.fulfill({status:502,contentType:'application/json',body:'{}'});
  await page.route('**/api/baskets/preview',fail);await prepare.click();
  await page.locator('.pantry-review .error').waitFor();
  assert.match(await page.locator('.pantry-review .error').innerText(),/Tekrar deneyin/);
  await page.unroute('**/api/baskets/preview',fail);await prepare.click();await page.getByRole('heading',{name:'Sepetim',exact:true}).waitFor();
  await page.getByRole('button',{name:'Başka Öner',exact:true}).click();
  assert.equal(await page.locator('.basket-preview').count(),0);
  await page.locator('#craving').fill('sushi');await submit.click();
  await page.getByText(/Bu tercihlere uygun tarif bulunamadı/).first().waitFor();
  assert.equal(await page.locator('.recipe-card').count(),0);
  console.log('PASS: Phase 0/1 API regressions, multi-recipe allocation 600-400=200, one recommendation/cycling/acceptance, recipe, pantry quantities, unknown stock, optional policy, basket arithmetic/provenance, local checklist/reset, incompatible units, mobile layout, loading/error/retry/empty states');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
