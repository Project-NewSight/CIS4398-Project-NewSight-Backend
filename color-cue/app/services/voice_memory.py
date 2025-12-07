class AddItemState:
    """
    Tracks multi-step state for voice-driven ADD ITEM FLOW.
    """

    # --- conversation state machine ---
    state = "idle"
    # valid states:
    # "idle", "awaiting_first_capture", "awaiting_item_confirmation",
    # "awaiting_tag_capture", "tag_captured", "awaiting_genre", "awaiting_notes",
    # "ready_to_save"

    # --- data we carry across steps ---
    item_features = None              # from detect_all() on clothing photo
    material = None                   # from tag OCR
    washing_instructions = None       # from tag OCR
    genre = None
    notes = None
    user_id = None
    closet_id = None

    @classmethod
    def reset(cls):
        cls.state = "idle"
        cls.item_features = None
        cls.material = None
        cls.washing_instructions = None
        cls.genre = None
        cls.notes = None
        cls.user_id = None
        cls.closet_id = None
