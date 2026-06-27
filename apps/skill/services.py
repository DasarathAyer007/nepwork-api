from apps.skill.models import Skill


class SkillService:
    @staticmethod
    def get_or_create_skills(skill_names):
        skills = []

        print(f"Skill names received: {skill_names}")  # Debugging line

        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name=name.strip())
            skills.append(skill)

        return skills
