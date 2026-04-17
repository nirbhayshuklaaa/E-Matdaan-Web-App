// ==========================
// AGE CALCULATOR
// ==========================
function calculateAge() {

    let dob = document.getElementById("dob").value;
    let result = document.getElementById("result");

    if (dob === "") {
        result.innerHTML = "⚠️ Please select date of birth";
        return;
    }

    let birthDate = new Date(dob);
    let today = new Date();

    let age = today.getFullYear() - birthDate.getFullYear();

    let monthDiff = today.getMonth() - birthDate.getMonth();

    // Adjust age if birthday not yet occurred
    if (
        monthDiff < 0 ||
        (monthDiff === 0 && today.getDate() < birthDate.getDate())
    ) {
        age--;
    }

    // Future date check
    if (birthDate > today) {
        result.innerHTML = "❌ Invalid Date of Birth";
        return;
    }

    // ✅ ELIGIBILITY CHECK
    if (age >= 18) {
        result.innerHTML = `🎉 You are <b>${age}</b> years old — <span style="color:green;">Eligible to Vote ✅</span>`;
    } else {
        result.innerHTML = `❌ You are <b>${age}</b> years old — <span style="color:red;">Not Eligible to Vote (Must be 18+) 🚫</span>`;
    }
}

// ==========================
// ACTIVE ELECTION
// ==========================
function showElection(){

let state = document.getElementById("stateSelect").value;

if(state==""){
return;
}

fetch("/get_election/" + state)
.then(response => response.json())
.then(data => {

document.getElementById("title").innerHTML = data.title;
document.getElementById("state").innerHTML = data.state;
document.getElementById("type").innerHTML = data.type;
document.getElementById("assembly").innerHTML = data.assembly;
document.getElementById("seat").innerHTML = data.seat;
document.getElementById("status").innerHTML = data.status;

})
.catch(error => {
console.log(error);
});

}
function openContact(){
document.getElementById("contactModal").style.display="block";
}

function closeContact(){
document.getElementById("contactModal").style.display="none";
}