const socket = io();
const bidEl = document.getElementById("bid");
const countdownCircle = document.getElementById("timer-circle");
const bidHistoryEl = document.getElementById("bid-history");
const hammer = new Audio("/static/sounds/hammer.mp3");
const applause = new Audio("/static/sounds/applause.mp3");
const CIRCLE_LENGTH = 879;

socket.on('update', (item)=>{
    document.getElementById("item-name").innerText = item.name || "Waiting...";
    animateBid(item.current_bid || 0);
    document.getElementById("status").innerText = item.status || "--";
    document.getElementById("category-badge").innerText = item.category || "";
    if(item.image) document.getElementById("item-img").src = "/uploads/"+item.image;
    if(item.team_logo && item.status.includes("SOLD")) {
        document.getElementById("team-logo").src="/uploads/"+item.team_logo;
        document.getElementById("team-logo").style.display="block";
    } else document.getElementById("team-logo").style.display="none";

    if(item.stats){
        document.getElementById("matches").innerText=item.stats.Matches;
        document.getElementById("runs").innerText=item.stats.Runs;
        document.getElementById("avg").innerText=item.stats.Average;
        document.getElementById("sr").innerText=item.stats["Strike Rate"];
        document.getElementById("wickets").innerText=item.stats.Wickets;
        document.getElementById("econ").innerText=item.stats.Economy;
    }

    if(item.status.includes("SOLD")){
        applause.play().catch(()=>{});
        showBanner("SOLD ✅","#00ff99");
    }
    if(item.status.includes("UNSOLD")){
        showBanner("UNSOLD ❌","#ff4444");
    }
});

socket.on('timer', (data)=>{
    const offset = CIRCLE_LENGTH * data.time / 20;
    countdownCircle.style.strokeDashoffset = offset;
});

socket.on('bid_history', (history)=>{
    bidHistoryEl.innerHTML = "<strong>Bid History:</strong> "+history.join(", ");
    hammer.play().catch(()=>{});
});

function showBanner(text,color){
    const banner = document.getElementById("banner");
    banner.innerText=text;
    banner.style.background=color;
    banner.style.display="flex";
    setTimeout(()=>banner.style.display="none",4000);
}

// Animate bid increment smoothly
let currentDisplayedBid = 0;
function animateBid(target){
    const increment = (target - currentDisplayedBid)/10;
    if(Math.abs(target - currentDisplayedBid)<1){
        currentDisplayedBid = target;
        bidEl.innerText = "₹"+currentDisplayedBid+" L";
        return;
    }
    currentDisplayedBid += increment;
    bidEl.innerText = "₹"+Math.round(currentDisplayedBid)+" L";
    requestAnimationFrame(()=>animateBid(target));
}
