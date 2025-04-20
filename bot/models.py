from django.db import models
from asgiref.sync import sync_to_async


class TgUser(models.Model):
    chat_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    is_private = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_super_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} ({self.chat_id})"
    
    @classmethod
    @sync_to_async
    def get_by_chat_id(cls, chat_id):
        try:
            return cls.objects.get(chat_id=chat_id)
        except cls.DoesNotExist:
            return None

    @classmethod
    @sync_to_async
    def create_tg_user(cls, chat_id, full_name, is_private=False, is_admin=False, is_super_admin=False):
        return cls.objects.create(
            chat_id=chat_id,
            full_name=full_name,
            is_private=is_private,
            is_admin=is_admin,
            is_super_admin=is_super_admin
        )

    @sync_to_async
    def update_is_private(self, is_private=False):
        self.is_private = is_private
        self.save()
        return self

    
class Group(models.Model):
    chat_id = models.BigIntegerField(unique=True)
    title = models.CharField(null=True, blank=True, max_length=255)
    required_members = models.IntegerField(default=0)
    required_channel = models.BigIntegerField(default=None, null=True, blank=True)
    required_channel_username = models.CharField(max_length=255, null=True, blank=True)
    required_channel_title = models.CharField(max_length=255, null=True, blank=True, default=None)
    is_admin = models.BooleanField(default=False)

    @classmethod
    @sync_to_async
    def get_by_chat_id(cls, chat_id):
        try:
            return cls.objects.get(chat_id=chat_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    @sync_to_async
    def create_group(cls, chat_id, title=None, required_members=0, required_channel=None, is_admin=False):
        return cls.objects.create(
            chat_id=chat_id,
            title=title,
            required_members=required_members,
            required_channel=required_channel,
            is_admin=is_admin
        )

    @sync_to_async
    def update_group_admin_status(self, is_admin=False):
        self.is_admin = is_admin
        return self.save()

    @sync_to_async
    def update_required_member_count(self, required_count):
        self.required_members = required_count
        return self.save()

    @sync_to_async
    def update_required_channel(self, required_channel, required_channel_title, required_channel_username=None):
        self.required_channel = required_channel
        self.required_channel_title = required_channel_title
        self.required_channel_username = required_channel_username
        return self.save()

    def __str__(self):
        return f"{self.title}: {self.chat_id}"


class GroupMember(models.Model):
    group_chat = models.ForeignKey(Group, on_delete=models.CASCADE)
    user_chat = models.ForeignKey(TgUser, on_delete=models.CASCADE)
    invite_count = models.BigIntegerField(default=0)  # Default qiymat qo'shildi

    def __str__(self):
        return f"{self.user_chat} in {self.group_chat}"

    @classmethod
    @sync_to_async
    def get_group_member(cls, chat_id, tg_user_id):
        try:
            return cls.objects.select_related("group_chat", "user_chat").get(
                group_chat__chat_id=chat_id,
                user_chat__chat_id=tg_user_id
            )
        except cls.DoesNotExist:
            return None
        except Exception as e:
            print(f"Xatolik get_group_member da: {str(e)}")
            return None

    @classmethod
    @sync_to_async
    def join_group_member(cls, chat_id, tg_user_id):
        try:
            group = Group.objects.get(chat_id=chat_id)
            user = TgUser.objects.get(chat_id=tg_user_id)

            cls.objects.create(group_chat=group, user_chat=user, invite_count=0)

            return cls.objects.select_related("group_chat", "user_chat").get(
                group_chat=group,
                user_chat=user
            )
        except Exception as e:
            print(f"Xatolik join_group_member da: {str(e)}")
            return None

    @sync_to_async
    def update_count(self):
        try:
            self.invite_count += 1
            self.save()
            return self
        except Exception as e:
            print(f"Xatolik update_count da: {str(e)}")
            return None


class GroupMemberInvitedHistory(models.Model):
    id = models.BigAutoField(primary_key=True)  # Avtomatik ID
    group_member = models.ForeignKey(GroupMember, on_delete=models.CASCADE,
                                     related_name='invited_history')  # GroupMember bilan bog'lanish
    invited_chat_id = models.BigIntegerField()  # Taklif qilingan foydalanuvchining chat_id si

    def __str__(self):
        return f"Invite history for {self.group_member} - Invited: {self.invited_chat_id}"

    @classmethod
    @sync_to_async
    def create_invite_history(cls, group_member, invited_chat_id):
        """
        Guruh a'zosining taklif tarixini yaratadi, agar u allaqachon mavjud bo'lmasa.

        Args:
            group_member: GroupMember obyekti.
            invited_chat_id: Taklif qilingan foydalanuvchining chat_id si.

        Returns:
            GroupMemberInvitedHistory obyekti yoki None, agar xatolik yuz bergan bo'lsa.
        """
        try:
            # Mavjudligini tekshirish
            existing_history = cls.objects.filter(
                group_member=group_member,
                invited_chat_id=invited_chat_id
            ).first()

            if existing_history:
                # Agar allaqachon mavjud bo'lsa, hech narsa qilmaslik va None qaytarish (yoki mavjud obyektni qaytarish)
                return None  # Yoki existing_history, agar qaytarish kerak bo'lsa

            # Agar mavjud bo'lmasa, yangi yaratish
            new_history = cls.objects.create(
                group_member=group_member,
                invited_chat_id=invited_chat_id
            )
            return new_history

        except Exception as e:
            print(f"Xatolik create_invite_history da: {str(e)}")
            return None


class Word(models.Model):
    word = models.CharField(max_length=255)

    def __str__(self):
        return str(self.word)

    @classmethod
    @sync_to_async
    def get_words(cls):
        """
        Ma'lumotlar bazasidan barcha taqiqlangan so'zlarni ro'yxat sifatida qaytaradi.

        Returns:
            list: Taqiqlangan so'zlar ro'yxati.
        """
        return list(cls.objects.values_list('word', flat=True))


class ChannelMember(models.Model):
    channel_chat = models.BigIntegerField()
    user_chat = models.BigIntegerField()

    class Meta:
        unique_together = ('channel_chat', 'user_chat')  # Bu ikkala ustun kombinatsiyasini unik qiladi.

    def __str__(self):
        return f"{self.user_chat} in channel {self.channel_chat}"

    @classmethod
    @sync_to_async
    def join_channel(cls, channel_id, user_id):
        obj, created = cls.objects.get_or_create(
            channel_chat=channel_id,
            user_chat=user_id
        )
        return created  # True agar yangi yaratilgan bo'lsa, aks holda False

    @classmethod
    @sync_to_async
    def check_member(cls, channel_id, user_id):
        return cls.objects.filter(
            channel_chat=channel_id,
            user_chat=user_id
        ).exists()

    @classmethod
    @sync_to_async
    def remove_member(cls, channel_id, user_id):
        try:
            member = cls.objects.get(
                channel_chat=channel_id,
                user_chat=user_id
            )
            member.delete()
            return True
        except cls.DoesNotExist:
            return False


class GroupAdmin(models.Model):
    group_chat = models.ForeignKey(Group, on_delete=models.CASCADE)
    user_chat = models.ForeignKey(TgUser, on_delete=models.CASCADE)

    def __str__(self):
        return f"Admin {self.user_chat} of {self.group_chat}"

    @classmethod
    @sync_to_async
    def get_group_admins(cls, group_chat):
        return list(cls.objects.select_related("user_chat").filter(group_chat__chat_id=group_chat))

    @classmethod
    @sync_to_async
    def check_admin(cls, group_id, user_id):
        """
        Tekshiradi, foydalanuvchi guruhda admin ekanligini.

        Args:
            group_id: Guruhning chat_id si.
            user_id: Foydalanuvchining chat_id si.

        Returns:
            bool: Agar foydalanuvchi admin bo'lsa True, aks holda False.
        """
        return cls.objects.filter(
            group_chat__chat_id=group_id,
            user_chat__chat_id=user_id
        ).exists()


    @classmethod
    @sync_to_async
    def join_group_admin(cls, group, tg_user):
        """
        Guruhga yangi admin qo'shadi, agar u allaqachon admin bo'lmasa.

        Args:
            group: Group obyekti (guruh).
            tg_user: TgUser obyekti (foydalanuvchi).

        Returns:
            GroupAdmin obyekti yoki None, agar xatolik yuz bergan bo'lsa.
        """
        try:
            # Avval tekshirib ko'ramiz, agar foydalanuvchi allaqachon admin bo'lsa
            existing_admin = cls.objects.filter(
                group_chat=group,
                user_chat=tg_user
            ).first()

            if existing_admin:
                # Agar allaqachon mavjud bo'lsa, yangi qo'shmaslik va mavjud obyektni qaytarish
                return existing_admin

            # Agar mavjud bo'lmasa, yangi admin qo'shish
            new_admin = cls.objects.create(group_chat=group, user_chat=tg_user)

            # Yangi qo'shilgan adminni qaytarish
            return cls.objects.select_related("group_chat", "user_chat").get(
                group_chat=group,
                user_chat=tg_user
            )

        except Exception as e:
            print(f"Xatolik yuz berdi join_group_admin da: {str(e)}")
            return None

    @classmethod
    @sync_to_async
    def remove_group_admin(cls, group_chat_id, tg_user_chat_id):
        """
        Guruhdagi ma'lum bir foydalanuvchining adminlik statusini o'chiradi.

        Args:
            group_chat_id (int): Guruhning chat_id si.
            tg_user_chat_id (int): Foydalanuvchining chat_id si.

        Returns:
            bool: Operatsiya muvaffaqiyatli bo'lsa True, aks holda False.
        """
        try:
            admin = cls.objects.filter(
                group_chat__chat_id=group_chat_id,
                user_chat__chat_id=tg_user_chat_id
            )
            if admin.exists():
                admin.delete()
                return True
            else:
                return False
        except Exception as e:
            print(f"Xatolik yuz berdi: {str(e)}")
            return False
