class ActivityType:
    VIEW = "VIEW"
    CLICK = "CLICK"
    SAVE = "SAVE"
    UNSAVE = "UNSAVE"
    APPLY = "APPLY"
    REQUEST = "REQUEST"
    SEARCH = "SEARCH"

    CHOICES = [
        (VIEW, "View"),
        (CLICK, "Click"),
        (SAVE, "Save"),
        (UNSAVE, "Unsave"),
        (APPLY, "Apply"),
        (REQUEST, "Request"),
        (SEARCH, "Search"),
    ]


class ObjectType:
    JOB = "JOB"
    SERVICE = "SERVICE"

    CHOICES = [
        (JOB, "Job"),
        (SERVICE, "Service"),
    ]


ACTIVITY_WEIGHTS = {
    ActivityType.VIEW: 1,
    ActivityType.UNSAVE: 1,
    ActivityType.CLICK: 2,
    ActivityType.SEARCH: 3,
    ActivityType.SAVE: 5,
    ActivityType.APPLY: 10,
    ActivityType.REQUEST: 10,
}
