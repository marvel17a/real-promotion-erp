(function(){
  const form = document.getElementById('productForm');
  if (!form) return; // Exit if no form on page

  const MAX_IMG_SIZE = 2 * 1024 * 1024;  // 2MB
  const imgTypes = ['image/jpeg', 'image/jpg', 'image/png'];

  const imgInput = document.getElementById('imageInput');

  function showError(name, msg){
    const el = form.querySelector(`[name="${name}"]`);
    const box = form.querySelector(`[data-error-for="${name}"]`);
    if (el) el.classList.add('is-invalid');
    if (box) box.textContent = msg || '';
  }
  function clearError(name){
    const el = form.querySelector(`[name="${name}"]`);
    const box = form.querySelector(`[data-error-for="${name}"]`);
    if (el) el.classList.remove('is-invalid');
    if (box) box.textContent = '';
  }

  function validateRequired(name, minLen=1){
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return true;
    const v = el.value.trim();
    if (v.length < minLen){
      showError(name, 'This field is required');
      return false;
    }
    clearError(name); 
    return true;
  }

  function validateNumber(name, isRequired, minVal = 0) {
    const el = form.querySelector(`[name="${name}"]`);
    if (!el) return true;
    const v = el.value.trim();
    
    if (isRequired && v.length === 0) {
      showError(name, 'This field is required');
      return false;
    }
    
    if (v.length > 0) { // Only validate if not empty
      const num = parseFloat(v);
      if (isNaN(num)) {
        showError(name, 'Must be a valid number');
        return false;
      }
      if (num < minVal) {
        showError(name, `Must be ${minVal} or greater`);
        return false;
      }
    }
    
    clearError(name);
    return true;
  }

  // File validations
  if (imgInput){
    imgInput.addEventListener('change', ()=>{
      clearError('image');
      const f = imgInput.files[0];
      if (!f) return;
      if (!imgTypes.includes(f.type)) { showError('image','Only JPG/PNG allowed'); imgInput.value=''; return; }
      if (f.size > MAX_IMG_SIZE) { showError('image','Max size 2MB'); imgInput.value=''; return; }
    });
  }

  // Submit validation
  form.addEventListener('submit', async (e)=>{
    let ok = true;
    ok &= validateRequired('name', 2);
    ok &= validateNumber('price', true, 0);
    ok &= validateNumber('purchase_price', false, 0); // Not required, but must be valid if present
    ok &= validateNumber('stock', true, 0);

    if (!ok){ 
      e.preventDefault(); 
    }
  });
})();
