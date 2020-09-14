let animation = anime
  .timeline()
  .add({
    targets: ".ml5 .line",
    opacity: [0.5, 1],
    scaleX: [0, 1],
    easing: "easeInOutExpo",
    duration: 700,
  })
  .add({
    targets: ".ml5 .line",
    duration: 600,
    easing: "easeOutExpo",
    translateY: (el, i) => -0.625 * 2 + 0.67 * 3 * i + "em",
  })
  .add({
    targets: ".ml5 .letters",
    opacity: [0, 1],
    translateX: ["0.5em", 0],
    easing: "easeOutElastic",
    duration: 1000,
    offset: "-=300",
  })
  .add({
    targets: ".ml5",
    opacity: 0,
    duration: 800,
    easing: "easeOutExpo",
    delay: 1000,
  })
  .add({
    targets: ".ml6 .name",
    opacity: [0, 1],
    duration: 1000,
    easing: "easeInOutExpo",
    scale: [1, 0.5],
    translateY: (el, i) => 0.8 - 0.3 * i + "em",
  })
  .add({
    targets: ".ml6 .skills1",
    opacity: [0, 1],
    duration: 1200,
    easing: "easeInOutExpo",
  })
  .add({
    targets: ".ml6 .skills2",
    opacity: [0, 1],
    duration: 1200,
    easing: "easeInOutExpo",
  })
  .add({
    targets: ".ml6 .skills3",
    opacity: [0, 1],
    duration: 1200,
    easing: "easeInOutExpo",
  })
  .add({
    targets: ".enter-button",
    opacity: [0, 1],
    duration: 1200,
    easing: "easeInOutExpo",
  });
