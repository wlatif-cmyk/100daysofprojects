// Simple Arduino project generator with gradually increasing difficulty
(function(){
  const projectList = [
    {title:"LED Blink Starter", difficulty:1, desc:"Blink an LED using the builtin Blink example. Learn digitalWrite and delay."},
    {title:"Button Piano", difficulty:2, desc:"Wire buttons to play tones on a buzzer. Practice digital input and tone()."},
    {title:"Night Light", difficulty:2, desc:"Use a photoresistor to control LED brightness with analogRead and PWM."},
    {title:"RGB Colour Changer", difficulty:3, desc:"Control an RGB LED with potentiometers to mix colors using PWM."},
    {title:"Servo Gesture", difficulty:3, desc:"Move a servo using input from a potentiometer or button sequence."},
    {title:"Temperature Monitor", difficulty:4, desc:"Read a temperature sensor (e.g., TMP36) and display readings on serial or LEDs."},
    {title:"Motion-Triggered Fan", difficulty:4, desc:"Use a PIR sensor to switch on a small fan or motor with a transistor."},
    {title:"Morse Transmitter", difficulty:5, desc:"Encode text into Morse and blink it with an LED or buzzer."},
    {title:"LCD Project Log", difficulty:5, desc:"Show sensor data on a 16x2 LCD or OLED, learn I2C basics."},
    {title:"Plant Watering Assistant", difficulty:6, desc:"Use moisture sensor + pump with thresholds to automatically water a plant."},
    {title:"Ultrasonic Range Finder", difficulty:6, desc:"Measure distance with HC-SR04 and act on proximity readings."},
    {title:"Light-Following Robot", difficulty:7, desc:"Build a small robot that follows light using photoresistors and motors."},
    {title:"Gesture Controlled Lamp", difficulty:7, desc:"Use sensors to change lamp behavior with gestures or movement."},
    {title:"Weather Station", difficulty:8, desc:"Collect temp/humidity/pressure and log or display trends over time."},
    {title:"Bluetooth Remote", difficulty:8, desc:"Control outputs from a phone over Bluetooth (HC-05/06)."},
    {title:"Web-Connected Sensor", difficulty:9, desc:"Use ESP8266/ESP32 to send sensor data to a web dashboard."},
    {title:"Home Automation Hub", difficulty:9, desc:"Integrate multiple inputs and outputs, remote control, scheduling."},
    {title:"Computer Vision Robot", difficulty:10, desc:"Combine camera module/edge processing with Arduino-compatible microcontrollers for vision tasks."},
    {title:"Custom PCB Project", difficulty:10, desc:"Design and assemble a PCB for your final project; include silkscreen and footprints."}
  ];

  let currentLevel = 1; // grows gradually toward 10
  let used = [];

  const pullBtn = document.getElementById('pullBtn');
  const resetBtn = document.getElementById('resetBtn');
  const titleEl = document.getElementById('projectTitle');
  const titleTextEl = document.querySelector('#projectTitle .titleText');
  const descEl = document.getElementById('projectDesc');
  const diffEl = document.getElementById('projectDifficulty');
  const levelEl = document.getElementById('difficultyLevel');
  const card = document.getElementById('projectCard');

  function updateLevelDisplay(){ levelEl.textContent = Math.min(10, Math.max(1, Math.round(currentLevel))); }

  function pickProject(){
    // Gradually increase difficulty with a bit of randomness
    const target = Math.min(10, Math.max(1, Math.round(currentLevel + Math.random()*0.9)));
    // Prefer projects with difficulty in [target, target]
    const candidates = projectList.filter(p => p.difficulty === target && !used.includes(p.title));
    let pick;
    if(candidates.length) pick = candidates[Math.floor(Math.random()*candidates.length)];
    else {
      // fallback: find nearest difficulty available (unused)
      const fallback = projectList.filter(p => !used.includes(p.title)).sort((a,b)=>Math.abs(a.difficulty-target)-Math.abs(b.difficulty-target));
      pick = fallback[0] || projectList[Math.floor(Math.random()*projectList.length)];
    }
    if(!used.includes(pick.title)) used.push(pick.title);
    // increase difficulty a little for next time
    currentLevel = Math.min(10, currentLevel + 0.9 + Math.random()*0.4);
    return pick;
  }

  function showProject(proj){
    // set title text inside the span so we can animate it separately
    if (titleTextEl) titleTextEl.textContent = proj.title;
    else titleEl.textContent = proj.title;
    descEl.textContent = proj.desc;
    diffEl.textContent = `Difficulty: ${proj.difficulty}`;
    updateLevelDisplay();
    // animate emergence from the hat
    card.classList.remove('peek');
    card.classList.remove('emerge');
    // force reflow to restart animation
    void card.offsetWidth;
    card.classList.add('emerge');
    // animate title "idea" pop
    if(titleTextEl){
      titleTextEl.classList.remove('idea-burst');
      void titleTextEl.offsetWidth;
      titleTextEl.classList.add('idea-burst');
      // remove class after animation ends to allow replay
      setTimeout(()=> titleTextEl.classList.remove('idea-burst'), 1100);
    }
    // trigger confetti
    launchConfetti();
  }

  pullBtn.addEventListener('click', ()=>{
    const p = pickProject();
    showProject(p);
  });

  resetBtn.addEventListener('click', ()=>{
    currentLevel = 1; used = []; updateLevelDisplay();
    if (titleTextEl) titleTextEl.textContent = 'Ready?';
    else titleEl.textContent = 'Ready?';
    descEl.textContent = 'Click "Pull project" to reveal your next Arduino challenge.';
    diffEl.textContent = '';
    card.classList.remove('emerge');
    // tuck card back into the hat so it peeks again
    setTimeout(()=> card.classList.add('peek'), 140);
  });

  // Small confetti implementation
  const canvas = document.getElementById('confettiCanvas');
  const ctx = canvas.getContext('2d');
  let confettiPieces = [];

  function resizeCanvas(){
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  window.addEventListener('resize', resizeCanvas);
  resizeCanvas();

  function spawnConfetti(count=40){
    // Black, white, and brand yellow confetti to match the B/W UI with yellow accent
    const colors = ['#111111','#ffffff','#f6c02d'];
    for(let i=0;i<count;i++){
      confettiPieces.push({
        x: canvas.width/2 + (Math.random()-0.5)*200,
        y: canvas.height/2 - 40 + (Math.random()-0.5)*60,
        vx: (Math.random()-0.5)*6,
        vy: - (4 + Math.random()*8),
        size: 6 + Math.random()*8,
        color: colors[Math.floor(Math.random()*colors.length)],
        rot: Math.random()*360,
        vrot: (Math.random()-0.5)*10
      });
    }
  }

  function updateConfetti(){
    ctx.clearRect(0,0,canvas.width,canvas.height);
    for(let i=confettiPieces.length-1;i>=0;i--){
      const p = confettiPieces[i];
      p.vy += 0.18; // gravity
      p.x += p.vx; p.y += p.vy; p.rot += p.vrot;
      ctx.save();
      ctx.translate(p.x,p.y);
      ctx.rotate(p.rot * Math.PI/180);
      ctx.fillStyle = p.color;
      ctx.fillRect(-p.size/2, -p.size/2, p.size, p.size);
      ctx.restore();
      if(p.y > canvas.height + 50) confettiPieces.splice(i,1);
    }
    if(confettiPieces.length) requestAnimationFrame(updateConfetti);
  }

  function launchConfetti(){
    spawnConfetti(60);
    requestAnimationFrame(updateConfetti);
    // small secondary bursts
    setTimeout(()=>{ spawnConfetti(30); }, 350);
  }

  // initial peek
  setTimeout(()=>{ card.classList.add('peek'); }, 200);
  updateLevelDisplay();

})();
