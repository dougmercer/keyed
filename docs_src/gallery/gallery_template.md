# Example Gallery

<div class="grid cards" markdown>
{% for scene in scenes %}
-   __{{ scene.title }}__

    ---

    <video autoplay loop muted playsinline>
    <source src="/media/gallery/{{ scene.name }}.webm" type="video/webm">
    </video>
    
    {{ scene.description }}

    [:octicons-arrow-right-24: Example]({{ scene.name }}.md)
{% endfor %}
</div>
