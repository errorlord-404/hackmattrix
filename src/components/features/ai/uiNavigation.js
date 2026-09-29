export function navigateToUiAction(path, locationRef = window.location, historyRef = window.history, emit = window.dispatchEvent.bind(window)) {
  if (locationRef.protocol === 'file:') {
    locationRef.hash = `#${path}`;
    return;
  }
  historyRef.pushState({}, '', path);
  emit(new PopStateEvent('popstate'));
}
