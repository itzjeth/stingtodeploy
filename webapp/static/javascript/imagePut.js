
function previewImage(event) {
  const reader = new FileReader();
  reader.onload = function() {
    document.getElementById('preview-image').src = reader.result;
  };
  reader.readAsDataURL(event.target.files[0]);
}
