// Looks for matching URLs, and if something matches, forces the app to
// talk to the yombo gateway for the URL.

export default function(context) {
  console.log(context)

  const paths = ['/user/logout', '/system/restart'];

  if (paths.includes(context.route.fullPath)) {
    console.log("should logout.....");
    if (context.isDev) {
      return context.redirect("/devnoredirect")
    } else {
       window.location.href = "/user/logout";
    }
  }
}
