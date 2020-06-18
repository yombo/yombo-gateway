// Looks for matching URLs, and if something matches, exits the Frontend Vue application and talks directly to
// the webinterface library routes.
//
// Also if running in development, show a default page showing a capability isn't available for some tasks.

export default function(context) {
  const paths = ['/user/logout', '/system/restart', '/system/shutdown'];

  if (paths.includes(context.route.fullPath)) {
    if (context.isDev) {
      return context.redirect("/devnoredirect")
    } else {
       window.location.href = context.route.fullPath;
    }
  }
}
