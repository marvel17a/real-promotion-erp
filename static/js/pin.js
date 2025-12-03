document.addEventListener("DOMContentLoaded", function () {

    const pin = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    pin.addEventListener("keyup", function () {
        let p = this.value.trim();

        if (p.length === 6 && /^[0-9]+$/.test(p)) {

            fetch(`/api/pincode_lookup/${p}`)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        city.value = data.city;
                        district.value = data.district;
                        state.value = data.state;
                    } else {
                        city.value = "";
                        district.value = "";
                        state.value = "";
                    }
                });
        }
    });

    // Image preview
    document.getElementById("imageInput").addEventListener("change", function () {
        const img = document.getElementById("imagePreview");
        img.src = URL.createObjectURL(this.files[0]);
        img.style.display = "block";
    });

});
