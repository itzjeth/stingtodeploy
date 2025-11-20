$(window).on('scroll',function(){
    if($(window).scrollTop()){
        $('nav').addClass('black');
    }
    else{
        $('nav').removeClass('black');
    }
})
$(document).ready(function(){
        $('.menu-button-container').click(function(){
            $("nav ul").toggleClass("active")
    })
    })