/* auroraWX gallery modal: click a thumbnail, view the full-size asset.
 * Plain JS — no jQuery/MDB dependency. Mirrors the legacy aurora site. */
(function () {
  "use strict";

  var modal = document.getElementById("auroraModal");
  if (!modal) {
    return;
  }
  var bodyEl = modal.querySelector(".aurora-modal-body");
  var captionEl = modal.querySelector(".aurora-modal-caption");
  var closeEl = modal.querySelector(".aurora-modal-close");
  var current = null;

  function clearMedia() {
    if (current && current.pause) {
      current.pause();
    }
    bodyEl.innerHTML = "";
    current = null;
  }

  function open(trigger) {
    clearMedia();
    var el;
    if (trigger.getAttribute("data-type") === "video") {
      el = document.createElement("video");
      el.controls = true;
      el.autoplay = true;
      el.src = trigger.getAttribute("data-src");
    } else {
      el = document.createElement("img");
      el.src = trigger.getAttribute("data-src");
      el.alt = trigger.getAttribute("alt") || "";
    }
    bodyEl.appendChild(el);
    current = el;
    captionEl.textContent = trigger.getAttribute("data-title") || "";
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("aurora-modal-open");
  }

  function close() {
    clearMedia();
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("aurora-modal-open");
  }

  document.addEventListener("click", function (e) {
    var trigger = e.target.closest ? e.target.closest(".aurora-modal-trigger") : null;
    if (trigger) {
      e.preventDefault();
      open(trigger);
    }
  });
  closeEl.addEventListener("click", close);
  modal.addEventListener("click", function (e) {
    if (e.target === modal) {
      close();
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      close();
    }
  });

  /* Thumbnails may point at a video first frame (#t=0.5) when no real
   * thumbnail exists. Browsers that cannot decode it (e.g. Firefox) fire
   * an error — hide the broken img so the dark frame + play overlay show
   * instead. The trigger stays clickable via the frame. */
  document.querySelectorAll(".aurora-media-frame img").forEach(function (img) {
    function hide() {
      /* Hand the trigger role to the frame so the card stays clickable. */
      var frame = img.closest(".aurora-media-frame");
      if (frame && !frame.classList.contains("aurora-modal-trigger")) {
        frame.classList.add("aurora-modal-trigger");
        ["data-type", "data-src", "data-title"].forEach(function (attr) {
          frame.setAttribute(attr, img.getAttribute(attr));
        });
      }
      img.style.display = "none";
    }
    if (img.complete && img.naturalWidth === 0) {
      hide();
    }
    img.addEventListener("error", hide);
  });
})();
