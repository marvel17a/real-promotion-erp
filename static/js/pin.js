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

                        let PO = data[0].PostOffice[0];

                        let d = PO.District || "";
                        let s = PO.State || "";
                        let taluk = PO.Taluk || "";
                        let division = PO.Division || "";
                        let area = PO.Name || "";

                        let cityName = "";

                        // SMART INDIA-WIDE CITY LOGIC
                        if (taluk && taluk !== d) {
                            cityName = taluk;
                        } 
                        else if (division && division !== d) {
                            cityName = division;
                        } 
                        else {
                            cityName = area;  // Village / locality name
                        }

                        city.value = cityName;
                        district.value = d;
                        state.value = s;

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
