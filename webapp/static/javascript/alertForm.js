function validate_password() {

    let pass = document.getElementById('password').value;
    let confirm_pass = document.getElementById('confirm_pass').value;
    if (pass != confirm_pass) {
        document.getElementById('wrong_pass_alert').style.color = 'red';
        document.getElementById('wrong_pass_alert').innerHTML
            = 'Password not match';
        document.getElementById('create').disabled = true;
        document.getElementById('create').style.opacity = (0.1);
    } else {
        document.getElementById('wrong_pass_alert').style.color = 'green';
        document.getElementById('wrong_pass_alert').innerHTML =
            '';
        document.getElementById('create').disabled = false;
        document.getElementById('create').style.opacity = (1);
    }
   }