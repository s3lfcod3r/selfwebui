const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class Element{setAttribute(k,v){this[k+'Attribute']=v;}}
function make(tag,prop){class E extends Element{constructor(){super();this.tagName=tag;}}Object.defineProperty(E.prototype,prop,{configurable:true,get(){return this.value;},set(v){this.value=v;}});return E;}
const Script=make('SCRIPT','src'),Link=make('LINK','href'),Image=make('IMG','src');
const location={href:'http://localhost:3082/api/browser/frame/test/http/192.0.2.21%3A3000/dashboard/home',origin:'http://localhost:3082'};
const s=fs.readFileSync(process.argv[2],'utf8');vm.runInNewContext(s.slice(0,s.indexOf('  function report()'))+'})();',{URL,location,Element,HTMLScriptElement:Script,HTMLLinkElement:Link,HTMLImageElement:Image,window:{__cptrBrowser:{session:'test',url:'http://192.0.2.21:3000/dashboard/home'},fetch(){},WebSocket:class{}}});
let el=new Script;el.src='/_next/chunk.js?v=1';assert.equal(el.src,'/api/browser/frame/test/http/192.0.2.21%3A3000/_next/chunk.js?v=1');el.src=el.src;assert.equal(el.src,'/api/browser/frame/test/http/192.0.2.21%3A3000/_next/chunk.js?v=1');el.setAttribute('src','/_next/dynamic.js');assert.ok(el.srcAttribute.endsWith('/http/192.0.2.21%3A3000/_next/dynamic.js'));
el.src='/api/browser/runtime.js';assert.equal(el.src,'/api/browser/runtime.js');el.src='data:text/javascript,0';assert.equal(el.src,'data:text/javascript,0');let css=new Link;css.href='/style.css';assert.ok(css.href.endsWith('/http/192.0.2.21%3A3000/style.css'));console.log('PASS: dynamic scripts, styles, attributes, idempotence, runtime and data URLs');

el.src='http://localhost:3082/dashboard/office?_rsc=test';assert.equal(el.src,'/api/browser/frame/test/http/192.0.2.21%3A3000/dashboard/office?_rsc=test');console.log('PASS: same-origin absolute routing');
