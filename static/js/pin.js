// static/js/pin.js
document.addEventListener("DOMContentLoaded", () => {
    const pin = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    pin.addEventListener("keyup", async () => {
        const p = pin.value.trim();

        if (p.length === 6 && /^\d+$/.test(p)) {
            let url = `https://api.postalpincode.in/pincode/${p}`;

            try {
                let response = await fetch(url);
                let data = await response.json();

                if (data[0].Status === "Success") {
                    let PO = data[0].PostOffice[0];

                    city.value = PO.Name || "";       // Correct City
                    district.value = PO.District || ""; // Correct District
                    state.value = PO.State || "";     // Correct State

                } else {
                    city.value = "";
                    district.value = "";
                    state.value = "";
                }
            } catch (err) {
                console.error("Pincode fetch error:", err);
            }
        }
    });
});


document.addEventListener("DOMContentLoaded", function () {
    const pin = document.getElementById("pincode");

    pin.addEventListener("keyup", () => {
        let p = pin.value.trim();

        if (p.length === 6 && /^\d+$/.test(p)) {
            fetch(`/api/pincode_lookup/${p}`)
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById("city").value = data.city;
                        document.getElementById("district").value = data.district;
                        document.getElementById("state").value = data.state;
                    } else {
                        console.log("Invalid!");
                    }
                })
                .catch(err => console.log(err));
        }
    });
});

