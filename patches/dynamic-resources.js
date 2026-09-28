  // Dynamic resources (for example webpack/Next.js chunks) must use the same
  // upstream route as resources present in the initial HTML document.
  function resourceUrl(value) {
    const raw = String(value);
    const current = new URL(raw, location.href);
    if (current.origin === location.origin && current.pathname === '/api/browser/runtime.js') return raw;
    return proxyUrl(raw);
  }
  for (const [type, property] of [[HTMLScriptElement, 'src'], [HTMLLinkElement, 'href'], [HTMLImageElement, 'src']]) {
    const descriptor = Object.getOwnPropertyDescriptor(type.prototype, property);
    if (!descriptor?.set || !descriptor.configurable) continue;
    Object.defineProperty(type.prototype, property, {
      ...descriptor,
      set(value) { return descriptor.set.call(this, resourceUrl(value)); }
    });
  }
  const originalSetAttribute = Element.prototype.setAttribute;
  Element.prototype.setAttribute = function(name, value) {
    const key = String(name).toLowerCase();
    if ((key === 'src' && ['SCRIPT','IMG'].includes(this.tagName)) ||
        (key === 'href' && this.tagName === 'LINK')) value = resourceUrl(value);
    return originalSetAttribute.call(this, name, value);
  };

