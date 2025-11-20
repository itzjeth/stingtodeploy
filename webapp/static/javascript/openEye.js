$(function(){

    $("body").on("click", ".eye-icon", function(){
  
      var eye = $(this).children("i");
  
      if(eye.hasClass("fa-eye-slash")){
        eye.removeClass("fa-eye-slash");
        eye.addClass("fa-eye");
        $(".wrap").addClass("eye-open");
        $(".pass").attr("type","text");
      }else {
        eye.removeClass("fa-eye");
        eye.addClass("fa-eye-slash");
        $(".wrap").removeClass("eye-open");
        $(".pass").attr("type","password");
      }
  
    });
  
  });