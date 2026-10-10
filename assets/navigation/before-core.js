/* Separate navigation extension; original V10 files remain byte-for-byte intact.
 * Normalize only while the synchronous legacy core installs its handlers, so
 * its old 1300ms deep-link timer is never scheduled. Restore the URL below;
 * actual entry waits for scene + texture readiness, not a guessed delay.
 */
window.__twinlightNavigationBoot = {hash: location.hash, version: 'navigation-1.0.0'};
if (location.hash === '#card' || location.hash === '#finale') {
  history.replaceState(history.state, '', '#galaxy');
}
