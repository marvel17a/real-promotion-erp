document.addEventListener("DOMContentLoaded", function () {
    const pinField = document.getElementById("pincode");
    const cityField = document.getElementById("city");
    const districtField = document.getElementById("district");
    const stateField = document.getElementById("state");

    pinField.addEventListener("keyup", function () {
        let pin = pinField.value.trim();

        if (pin.length === 6 && /^\d+$/.test(pin)) {
            fetch("https://api.postalpincode.in/pincode/" + pin)
                .then(res => res.json())
                .then(data => {
                    if (data[0].Status === "Success") {
                        let PO = data[0].PostOffice[0];

                        // Fill all three fields
                        cityField.value = PO.Name || "";      // Area/City
                        districtField.value = PO.District || "";
                        stateField.value = PO.State || "";
                    } else {
                        cityField.value = "";
                        districtField.value = "";
                        stateField.value = "";
                        console.error("Invalid pincode");
                    }
                })
                .catch(err => {
                    console.error("Error fetching pincode:", err);
                    cityField.value = "";
                    districtField.value = "";
                    stateField.value = "";
                });
        }
    });
});
