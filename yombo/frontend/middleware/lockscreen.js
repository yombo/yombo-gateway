// If the screen is supposed to be locked, force to lock page.

export default function(context) {
  if (context.route.fullPath !== "/lock" && context.store.state.frontend.settings.lockScreenLocked === true) {
    return context.redirect('/lock')
  }
}
