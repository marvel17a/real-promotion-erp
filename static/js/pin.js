// static/js/pin
document.addEventListener("DOMContentLoaded", () => {
    const pin = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    pin.addEventListener("keyup", async () => {
        const p = pin.value.trim();

        if (p.length === 6 && /^\d+$/.test(p)) {
            try {
                let url = `https://api.postalpincode.in/pincode/${p}`;
                let response = await fetch(url);
                let data = await response.json();

                if (data[0].Status === "Success") {
                    let PO = data[0].PostOffice[0];
                    city.value = PO.District || "";
                    district.value = PO.District || "";
                    state.value = PO.State || "";
                } else {
                    city.value = "";
                    district.value = "";
                    state.value = "";
                }
            } catch (e) {
                console.log("Pincode API Error:", e);
            }
        }
    });
});
