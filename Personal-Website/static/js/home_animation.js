let animationHome = anime.timeline().add({
  targets: ".profile-picture",
  opacity: 1,
  duration: 400,
  scale:[0.5,1]
})
.add({
  targets: ".about-me",
  opacity: 1,
  easing: "easeInOutExpo",
  duration: 1000,
  scale:[0,1],
})
.add({
  targets:'.circle-link',
  opacity:1,
  scale:[0,1],
  easing: "easeInOutExpo",
  delay: anime.stagger(700),
})
.add({
  targets: ".intro-heading",
  opacity: 1,
  easing: "easeInOutExpo",
  duration: 800,
  scale:[0,1]
})
.add({
  targets: ".intro-description",
  opacity: 1,
  easing: "easeInOutExpo",
  duration: 400,
  scale:[0,1]
})