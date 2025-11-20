scrollOffsetFunction = function() {
    var navElements = document.getElementsByClassName("c-navbar");
    if (typeof navElements[0] !== "undefined") {
      var navRect = navElements[0].getBoundingClientRect();
      var navStyle = getComputedStyle(navElements[0]);  
    if (navStyle.position === "sticky" || navStyle.position === "fixed") {
        return navRect.bottom - navRect.top + 30;
      }
    }
    return 0;
  }