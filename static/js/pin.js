document.addEventListener("DOMContentLoaded", function () {
    const pin = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    pin.addEventListener("keyup", function () {
        let pincode = pin.value.trim();

        if (pincode.length !== 6 || !/^\d+$/.test(pincode)) {
            return;
        }

        // Fetch from stable API
        fetch("https://postalpincode.in/api/pincode/" + pincode)
            .then(response => response.json())
            .then(data => {
                if (data.Status !== "Success") {
                    city.value = "";
                    district.value = "";
                    state.value = "";
                    return;
                }

                let PO = data.PostOffice[0];

                // Determine correct CITY/TALUKA
                let cityName = "";

                if (PO.Block && PO.Block.trim() !== "") {
                    cityName = PO.Block;            // Best option
                } else if (PO.Name && PO.Name.trim() !== "") {
                    cityName = PO.Name;             // Secondary option
                } else {
                    cityName = PO.District;         // Fallback
                }

                city.value = cityName;
                district.value = PO.District || "";
                state.value = PO.State || "";
            })
            .catch(err => {
                console.error("Pincode lookup error:", err);
                city.value = "";
                district.value = "";
                state.value = "";
            });
    });
});
