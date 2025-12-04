document.addEventListener("DOMContentLoaded", () => {
    const pin = document.getElementById("pincode");
    const city = document.getElementById("city");
    const district = document.getElementById("district");
    const state = document.getElementById("state");

    async function fetchPincodeDetails(pincode) {
        const url = https://api.postalpincode.in/pincode/${pincode};

        try {
            const response = await fetch(url);
            const data = await response.json();

            if (!data || data[0].Status !== "Success") {
                city.value = "";
                district.value = "";
                state.value = "";
                return;
            }

            let po = data[0].PostOffice[0];

            // CITY/TALUKA SELECTION PRIORITY
            // 1. Block (Taluka)
            // 2. Name (Local Post Office Area)
            // 3. District
            let cityValue = po.Block && po.Block.trim() !== "" ? po.Block :
                            po.Name && po.Name.trim() !== "" ? po.Name :
                            po.District;

            city.value = cityValue;
            district.value = po.District;
            state.value = po.State;

        } catch (err) {
            // Completely safe fallback — no page crash
            console.error("Pincode API error:", err);

            city.value = "";
            district.value = "";
            state.value = "";
        }
    }

    pin.addEventListener("input", () => {
        let pincode = pin.value.trim();

        if (pincode.length === 6 && /^\d+$/.test(pincode)) {
            fetchPincodeDetails(pincode);
        }
    });
});
