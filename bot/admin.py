from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import TgUser, Group, GroupMember, Word, ChannelMember, GroupAdmin, GroupMemberInvitedHistory

from django.contrib.auth.models import User, Group as DGroup

# Avval standart registratsiyani bekor qilamiz
admin.site.unregister(User)
admin.site.unregister(DGroup)


@admin.register(TgUser)
class TgUserAdmin(ModelAdmin):
    list_display = ('chat_id', 'full_name', 'is_private', 'is_admin', 'is_super_admin')
    search_fields = ('chat_id', 'full_name')
    readonly_fields = ('chat_id', 'full_name', 'is_private', 'is_super_admin')
    list_filter = ('is_admin', 'is_private', 'is_super_admin')
    

@admin.register(Group)
class GroupAdminModel(ModelAdmin):
    list_display = ('chat_id', 'title', 'required_members', 'required_channel', 'required_channel_username', 'required_channel_title', 'is_admin')
    search_fields = ('chat_id', 'title', 'required_channel_title',)
    list_filter = ('is_admin', )
    readonly_fields = ('chat_id', 'required_members', 'required_channel', 'required_channel_title', 'required_channel_username')
    

@admin.register(GroupMember)
class GroupMemberAdmin(ModelAdmin):
    list_display = ('group_chat', 'user_chat', 'invite_count')
    search_fields = ('group_chat__chat_id', 'user_chat__chat_id')
    readonly_fields = ('group_chat', 'user_chat')
    list_filter = ('group_chat', 'user_chat')
    

@admin.register(Word)
class WordAdmin(ModelAdmin):
    list_display = ('word',)
    search_fields = ('word',)
    

@admin.register(ChannelMember)
class ChannelMemberAdmin(ModelAdmin):
    list_display = ('channel_chat', 'user_chat')
    search_fields = ('channel_chat__chat_id', 'user_chat__chat_id')
    readonly_fields = ('channel_chat', 'user_chat')


@admin.register(GroupAdmin)
class GroupAdminModel(ModelAdmin):
    list_display = ('group_chat', 'user_chat')
    search_fields = ('group_chat__chat_id', 'user_chat__chat_id')
    readonly_fields = ('group_chat', 'user_chat')  

@admin.register(GroupMemberInvitedHistory)
class GroupMemberInvitedHistoryAdmin(ModelAdmin):
    list_display = ('group_member', 'invited_chat_id')
    list_filter = ('group_member__group_chat', 'group_member__user_chat')
    search_fields = ('invited_chat_id', 'group_member__user_chat__full_name', 'group_member__user_chat__chat_id', 'group_member__group_chat__title', 'group_member__group_chat__chat_id')
    ordering = ('-id',)

    fieldsets = (
        (None, {
            'fields': ('group_member', 'invited_chat_id')
        }),
    )

    list_editable = ()


# Optional: You can customize these if needed
@admin.register(User)
class CustomUserAdmin(ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'is_staff', 'is_active')
    ordering = ('username',)

