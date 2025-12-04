document.addEventListener("DOMContentLoaded", () => {
    const pin = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    pin.addEventListener("input", async () => {
        const pincode = pin.value.trim();

        // Validate pincode length
        if (pincode.length !== 6 || !/^\d+$/.test(pincode)) {
            return;
        }

        const url = https://api.postalpincode.in/pincode/${pincode};

        try {
            const res = await fetch(url);
            const data = await res.json();

            if (!data || data[0].Status !== "Success") {
                city.value = "";
                district.value = "";
                state.value = "";
                return;
            }

            const PO = data[0].PostOffice[0];

            // City logic (Block → Name → District)
            let cityValue = PO.Block && PO.Block.trim() !== "" 
                            ? PO.Block 
                            : (PO.Name || PO.District);

            city.value = cityValue;
            district.value = PO.District || "";
            state.value = PO.State || "";

        } catch (err) {
            console.error("API failed:", err);
            city.value = "";
            district.value = "";
            state.value = "";
        }
    });
});
