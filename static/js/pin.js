document.addEventListener("DOMContentLoaded", function () {
    const pin = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    pin.addEventListener("keyup", function () {
        let p = pin.value.trim();

        if (p.length === 6 && /^\d+$/.test(p)) {

            fetch("https://api.postalpincode.in/pincode/" + p)
                .then(res => res.json())
                .then(data => {

                    if (data[0].Status === "Success") {

                        let PO = data[0].PostOffice[0];   // Always take first office

                        // -----------------------
                        // Find correct city/taluka
                        // -----------------------
                        let cityName = "";

                        if (PO.Division && PO.Division !== "") {
                            cityName = PO.Division;
                        }
                        else if (PO.Taluk && PO.Taluk !== "") {
                            cityName = PO.Taluk;
                        }
                        else {
                            cityName = PO.District; // fallback
                        }

                        // Autofill the fields
                        city.value = cityName;
                        district.value = PO.District || "";
                        state.value = PO.State || "";

                    } else {
                        city.value = "";
                        district.value = "";
                        state.value = "";
                    }
                })
                .catch(err => {
                    console.error("Pincode error:", err);
                    city.value = "";
                    district.value = "";
                    state.value = "";
                });
        }
    });
});
