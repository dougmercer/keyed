<div class="grid cards" markdown>
{% for func in easing_functions %}
-   __[:octicons-arrow-right-24: {{ func }}][keyed.easing.{{ func }}]__

    ---

    <video autoplay loop muted playsinline>
    <source src="/media/easing/{{ func }}.webm" type="video/webm">
    </video>
    
    
{% endfor %}
</div>

<style>
  /* Control number of columns in the grid */
  .md-typeset .grid {
    grid-template-columns: repeat(auto-fit, minmax(12rem, 1fr));
  }
  
  .grid.cards > * {
    background-color: transparent;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  
  .grid.cards > *:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  }
  
  .grid.cards video {
    width: 100%;
    display: block;
    background-color: transparent;
    margin-top: 0.5em;
    margin-bottom: 0.5em;
  }
  
  /* Media query for different screen sizes */
  @media (min-width: 1400px) {
    .md-typeset .grid {
      grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
    }
  }
  
  @media (max-width: 800px) {
    .md-typeset .grid {
      grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
    }
  }
  
  @media (max-width: 500px) {
    .md-typeset .grid {
      grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
    }
  }
</style>
