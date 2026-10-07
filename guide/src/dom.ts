export function element<T extends HTMLElement>(
  selector: string,
  constructor: { new (): T },
): T {
  const result = document.querySelector(selector);
  if (!(result instanceof constructor)) {
    throw new Error(`Expected ${constructor.name} at ${selector}`);
  }
  return result;
}

export function appendText<K extends keyof HTMLElementTagNameMap>(
  parent: HTMLElement,
  tag: K,
  text: string,
  className?: string,
): HTMLElementTagNameMap[K] {
  const child = document.createElement(tag);
  child.textContent = text;
  if (className) child.className = className;
  parent.append(child);
  return child;
}
