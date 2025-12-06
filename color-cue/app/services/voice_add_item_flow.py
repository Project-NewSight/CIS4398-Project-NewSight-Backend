from app.services.voice_memory import AddItemState

class AddItemFlowHandler:

    @staticmethod
    def start_flow():
        """User said 'add item' → begin flow."""
        AddItemState.reset()
        AddItemState.state = "awaiting_item_capture"

        return (
            "Okay, let's add a new clothing item. "
            "Lay the item flat in good lighting and say 'capture item' when you're ready."
        )

    @staticmethod
    def handle(text: str):
        """Main state machine for ADD ITEM."""
        t = text.lower()

        # ----------------------------------------------------------
        # FLOW START
        # ----------------------------------------------------------
        if "add item" in t:
            return {
                "step": "start",
                "TTS": AddItemFlowHandler.start_flow()
            }

        # ----------------------------------------------------------
        # STEP 1 — WAITING FOR ITEM PHOTO
        # ----------------------------------------------------------
        if AddItemState.state == "awaiting_item_capture":
            if "capture item" in t or t == "capture":
                AddItemState.state = "awaiting_item_confirmation"
                return {
                    "step": "item_photo_requested",
                    "TTS": "Okay, capturing the item. Hold on while I analyze it."
                }
            return None

        # ----------------------------------------------------------
        # STEP 2 — ITEM CONFIRMATION
        # ----------------------------------------------------------
        if AddItemState.state == "awaiting_item_confirmation":
            if any(w in t for w in ["yes", "correct", "looks good", "okay"]):
                AddItemState.state = "awaiting_tag_capture"
                return {
                    "step": "item_confirmed",
                    "TTS": "Great! Now show me the clothing tag and say 'capture tag' when you're ready."
                }

            if any(w in t for w in ["no", "wrong", "incorrect"]):
                AddItemState.reset()
                AddItemState.state = "awaiting_item_capture"
                return {
                    "step": "retry_item",
                    "TTS": "No problem. Lay the item flat again and say 'capture item' when you're ready."
                }

            return None

        # ----------------------------------------------------------
        # STEP 3 — TAG CAPTURE
        # ----------------------------------------------------------
        if AddItemState.state == "awaiting_tag_capture":
            if "capture tag" in t:
                AddItemState.state = "awaiting_genre"
                return {
                    "step": "tag_photo_requested",
                    "TTS": "Okay, capturing the clothing tag. Hold steady."
                }
            return None

        # ----------------------------------------------------------
        # STEP 4 — GENRE
        # ----------------------------------------------------------
        if AddItemState.state == "awaiting_genre":
            AddItemState.genre = text
            AddItemState.state = "awaiting_notes"
            return {
                "step": "genre_received",
                "TTS": "Got it. Now tell me any notes you'd like to save with this item."
            }

        # ----------------------------------------------------------
        # STEP 5 — NOTES
        # ----------------------------------------------------------
        if AddItemState.state == "awaiting_notes":
            AddItemState.notes = text
            AddItemState.state = "ready_to_save"
            return {
                "step": "notes_received",
                "TTS": "Perfect. Say 'save item' when you're ready to store this in your closet."
            }

        # ----------------------------------------------------------
        # STEP 6 — READY TO SAVE
        # ----------------------------------------------------------
        if AddItemState.state == "ready_to_save" and "save item" in t:
            return {
                "step": "save",
                "TTS": "Okay, saving your item now."
            }

        return None
