class NotchWidgetInterface:
    """Interface for notch widgets"""

    def on_show(self) -> None:
        """When showing the widget."""
        raise NotImplementedError("Subclasses must implement this method.")
