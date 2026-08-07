(function restoreUniverseTheme(windowRef, documentRef) {
  let savedTheme = null;
  try {
    savedTheme = windowRef.localStorage?.getItem('universe-theme');
  } catch {
    savedTheme = null;
  }
  if (savedTheme === 'dark') {
    documentRef.documentElement.dataset.theme = 'dark';
  }
})(window, document);
