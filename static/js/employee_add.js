(function(){
  const form = document.getElementById('employeeForm');
  const apiURL = '/api/check-employee';
  const MAX_IMG_SIZE = 2 * 1024 * 1024;  // 2MB
  const MAX_DOC_SIZE = 5 * 1024 * 1024;  // 5MB
  const imgTypes = ['image/jpeg', 'image/jpg', 'image/png'];
  const docTypes = ['application/pdf'];

  const imgInput = document.getElementById('imageInput');
  const imgPreview = document.getElementById('imagePreview');
  const docInput = document.getElementById('docInput');
  const docName = document.getElementById('docName');

  function showError(name, msg){
    const el = form.querySelector(`[name="${name}"]`);
    const box = form.querySelector(`[data-error-for="${name}"]`);
    if (el) el.classList.add('input-error');
    if (box) box.textContent = msg || '';
  }
  function clearError(name){
    const el = form.querySelector(`[name="${name}"]`);
    const box = form.querySelector(`[data-error-for="${name}"]`);
    if (el) el.classList.remove('input-error');
    if (box) box.textContent = '';
  }

  function validateRequired(name, minLen=1){
    const v = form.querySelector(`[name="${name}"]`).value.trim();
    if (v.length < minLen){
      showError(name, 'This field is required');
      return false;
    }
    clearError(name); return true;
  }
  function validateEmail(name){
    const v = form.querySelector(`[name="${name}"]`).value.trim();
    const ok = /^\S+@\S+\.\S+$/.test(v);
    if (!ok){ showError(name, 'Enter a valid email'); return false; }
    clearError(name); return true;
  }
  function validatePhone(name){
    const v = form.querySelector(`[name="${name}"]`).value.trim();
    const ok = /^\d{10}$/.test(v);
    if (!ok){ showError(name, 'Phone must be 10 digits'); return false; }
    clearError(name); return true;
  }

  // Debounced duplicate check
  let timers = {};
  function checkUnique(name){
    const el = form.querySelector(`[name="${name}"]`);
    const field = el.dataset.unique;  // name|email|phone
    if (!field) return;

    const value = el.value.trim();
    clearError(name);
    if (!value) return;

    if (timers[name]) clearTimeout(timers[name]);
    timers[name] = setTimeout(async ()=>{
      try {
        const url = `${apiURL}?field=${encodeURIComponent(field)}&value=${encodeURIComponent(value)}`;
        const res = await fetch(url);
        const data = await res.json();
        if (data.exists){
          showError(name, `${field.charAt(0).toUpperCase()+field.slice(1)} already exists`);
        }
      } catch(e){
        console.error('checkUnique error', e);
      }
    }, 350);
  }

  // File validations + preview
  if (imgInput && imgPreview){
    imgInput.addEventListener('change', ()=>{
      clearError('image');
      const f = imgInput.files[0];
      if (!f) { imgPreview.style.display='none'; return; }
      if (!imgTypes.includes(f.type)) { showError('image','Only JPG/PNG allowed'); imgInput.value=''; return; }
      if (f.size > MAX_IMG_SIZE) { showError('image','Max size 2MB'); imgInput.value=''; return; }

      const reader = new FileReader();
      reader.onload = ()=>{ imgPreview.src = reader.result; imgPreview.style.display='block'; };
      reader.readAsDataURL(f);
    });
  }
  if (docInput && docName){
    docInput.addEventListener('change', ()=>{
      clearError('document');
      const f = docInput.files[0];
      docName.textContent = f ? f.name : 'No file chosen';
      if (!f) return;
      if (!docTypes.includes(f.type)){ showError('document','Only PDF allowed'); docInput.value=''; return; }
      if (f.size > MAX_DOC_SIZE){ showError('document','Max size 5MB'); docInput.value=''; return; }
    });
  }

  // Listen to changes for uniqueness
  ['name','email','phone'].forEach(n=>{
    const el = form.querySelector(`[name="${n}"]`);
    if (!el) return;
    el.addEventListener('input', ()=> checkUnique(n));
    el.addEventListener('blur', ()=> checkUnique(n));
  });

  // Submit validation
  form.addEventListener('submit', async (e)=>{
    let ok = true;
    ok &= validateRequired('name', 2);
    ok &= validateRequired('position', 2);
    ok &= validateEmail('email');
    ok &= validatePhone('phone');
    ok &= validateRequired('status');
    ok &= validateRequired('city', 2);

    // If any duplicate messages visible, cancel
    ['name','email','phone'].forEach(n=>{
      const box = form.querySelector(`[data-error-for="${n}"]`);
      if (box && box.textContent.includes('exists')) ok = false;
    });

    if (!ok){ e.preventDefault(); }
  });
})();
