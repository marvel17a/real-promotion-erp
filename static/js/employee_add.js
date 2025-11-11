(function(){
  const form = document.getElementById('employeeForm');
  if (!form) return;

  const MAX_IMG_SIZE = 2 * 1024 * 1024;
  const MAX_DOC_SIZE = 5 * 1024 * 1024;
  const imgTypes = ['image/jpeg','image/jpg','image/png'];
  const docTypes = ['application/pdf'];

  const imgInput = document.getElementById('imageInput');
  const imgPreview = document.getElementById('imagePreview');
  const docInput = document.getElementById('docInput');
  const docName = document.getElementById('docName');

  function err(name,msg){
    const el=form.querySelector(`[name="${name}"]`);
    const box=form.querySelector(`[data-error-for="${name}"]`);
    el && el.classList.add('input-error');
    box && (box.textContent=msg||'');
  }
  function ok(name){
    const el=form.querySelector(`[name="${name}"]`);
    const box=form.querySelector(`[data-error-for="${name}"]`);
    el && el.classList.remove('input-error');
    box && (box.textContent='');
  }
  function need(name,min=1){
    const v=form.querySelector(`[name="${name}"]`).value.trim();
    if(v.length<min){err(name,'This field is required');return false}
    ok(name);return true;
  }
  function email(name){
    const v=form.querySelector(`[name="${name}"]`).value.trim();
    const good=/^\S+@\S+\.\S+$/.test(v);
    if(!good){err(name,'Enter a valid email');return false}
    ok(name);return true;
  }
  function phone(name){
    const v=form.querySelector(`[name="${name}"]`).value.trim();
    const good=/^\d{10}$/.test(v);
    if(!good){err(name,'Phone must be 10 digits');return false}
    ok(name);return true;
  }

  if (imgInput && imgPreview){
    imgInput.addEventListener('change', ()=>{
      ok('image');
      const f=imgInput.files[0];
      if(!f){ imgPreview.style.display='none'; return; }
      if(!imgTypes.includes(f.type)){ err('image','Only JPG/PNG allowed'); imgInput.value=''; return; }
      if(f.size>MAX_IMG_SIZE){ err('image','Max size 2MB'); imgInput.value=''; return; }
      const reader=new FileReader();
      reader.onload=()=>{ imgPreview.src=reader.result; imgPreview.style.display='block'; };
      reader.readAsDataURL(f);
    });
  }
  if (docInput && docName){
    docInput.addEventListener('change', ()=>{
      ok('document');
      const f=docInput.files[0];
      docName.textContent = f ? f.name : 'No file chosen';
      if(!f) return;
      if(!docTypes.includes(f.type)){ err('document','Only PDF allowed'); docInput.value=''; return; }
      if(f.size>MAX_DOC_SIZE){ err('document','Max size 5MB'); docInput.value=''; return; }
    });
  }

  form.addEventListener('submit',(e)=>{
    let good=true;
    good &= need('name',2);
    good &= need('position',2);
    good &= email('email');
    good &= phone('phone');
    good &= need('status');
    good &= need('city',2);
    if(!good) e.preventDefault();
  });
})();
