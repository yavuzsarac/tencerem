// Local HTTP checks; all numbers below are authored demo fixtures, never live prices.
const assert=require('node:assert/strict');
const backend=process.env.TEST_BACKEND_URL||'http://127.0.0.1:8016';
async function post(path,body){const r=await fetch(`${backend}/api/v1/${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.equal(r.status,200);return r.json();}
(async()=>{
 const markets=await (await fetch(`${backend}/api/v1/markets`)).json();
 assert.equal(markets.length,2);assert(markets.every(m=>m.data_source==='curated_demo'));
 const body={recipes:[{slug:'tavuklu-pilav',servings:5}],pantry:[
  {ingredient_id:'chicken_breast',quantity:'300',unit:'g'},{ingredient_id:'rice',quantity:'500',unit:'g'},
  {ingredient_id:'salt',quantity:'10',unit:'tsp'},{ingredient_id:'olive_oil',quantity:'10',unit:'tbsp'}]};
 const price=await post('baskets/price',{...body,retailer_id:'demo-a'});
 const line=price.estimate.items.find(i=>i.ingredient_id==='chicken_breast');
 assert.equal(line.required_missing_quantity,'200.000000');assert.equal(line.package_count,1);
 assert.equal(line.purchased_quantity,'500');assert.equal(Number(line.surplus_quantity),300);
 assert.equal(line.line_total,'90.00');assert.equal(price.estimate.basket_total,'110.00');
 console.log('PASS: demo catalog and pricing smoke; pantry-first packages, surplus, exact TRY strings');
 const compared=await post('baskets/compare',body);
 assert.equal(compared.recommended_retailer_id,'demo-b');assert.equal(compared.estimates[0].basket_total,'106.00');
 assert(compared.estimates.every(e=>e.complete));
 const partial=await post('baskets/compare',{recipes:body.recipes});
 assert.equal(partial.recommended_retailer_id,null);assert(partial.estimates.every(e=>!e.complete&&e.basket_total===null));
 const multi=await post('baskets/price',{retailer_id:'demo-a',recipes:[{slug:'tavuklu-pilav',servings:3},{slug:'tavuk-sote',servings:2}],pantry:[{ingredient_id:'chicken_breast',quantity:'200',unit:'g'}]});
 const chicken=multi.estimate.items.filter(i=>i.ingredient_id==='chicken_breast');
 assert.equal(chicken.length,1);assert.equal(Number(chicken[0].required_missing_quantity),400);assert.equal(chicken[0].package_count,1);
 console.log('PASS: demo comparison smoke; complete winner, partial total withheld, multi-recipe consolidation');
})().catch(e=>{console.error(e);process.exit(1);});
