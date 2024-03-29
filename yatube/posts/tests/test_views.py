from http import HTTPStatus

from django import forms
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, Follow

User = get_user_model()


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User_test')
        cls.group_slug = 'user_test_slug'
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=cls.group_slug,
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        # Создаем авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_users_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group_slug},
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': self.user},
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk},
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_create',
            ): 'posts/create_post.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk},
            ): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def check_post_context_on_page(self, first_object):
        self.assertEqual(first_object.text, self.post.text)
        self.assertEqual(first_object.author, self.post.author)
        self.assertEqual(first_object.group, self.post.group)

    def test_posts_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        test_object = response.context['page_obj'][0]
        self.check_post_context_on_page(test_object)

    def test_cache_index(self):
        response = self.authorized_client.get(reverse('posts:index'))
        post_deleted = Post.objects.get(id=self.post.pk)
        post_deleted.delete()
        response_anoth = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response.content, response_anoth.content)
        cache.clear()
        response_other = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response.content, response_other.content)

    def test_posts_group_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group_slug},
            )
        )
        index_post = response.context['page_obj'][0]
        self.check_post_context_on_page(index_post)

    def test_posts_user_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user},
            )
        )
        index_post = response.context['page_obj'][0]
        self.check_post_context_on_page(index_post)

    def test_posts_detail_page_show_correct_context(self):
        """Шаблон posts/post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk},
            )
        )
        self.assertEqual(
            response.context['post'].text,
            self.post.text,
        )
        self.assertEqual(
            response.context['post'].group,
            self.post.group,
        )
        self.assertEqual(
            response.context['post'].author,
            self.post.author,
        )

    def test_posts_create_page_show_correct_context(self):
        """Шаблон posts/creat_posts сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_posts_group_page_not_include_incorect_post(self):
        """Шаблон posts/group_list не содержит лишний пост."""
        Group.objects.create(
            title='test-title 2',
            slug='test-slug_2',
            description='Описание тестовой группы',
        )
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': 'test-slug_2'},
            )
        )
        for object in response.context['page_obj']:
            post_slug = object.group_slug
            self.assertNotEqual(post_slug, self.group.slug)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User_test')
        cls.group_slug = 'user_test_slug'
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=cls.group_slug,
            description='Тестовое описание',
        )
        cls.user_follower = User.objects.create_user(
            username='myuser_follower'
        )
        cls.following = Follow.objects.create(
            user=cls.user_follower,
            author=cls.user,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_follower)

    def test_user_follow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей.
        """
        Follow.objects.all().delete()
        follow_count_1 = Follow.objects.count()
        follow = Follow.objects.filter(
            author=self.user,
            user=self.user_follower,
        )
        self.assertEqual(follow.first(), None)
        response = self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                args=(self.user.username,)
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        follow_count_2 = Follow.objects.count()
        self.assertEqual(follow_count_2, follow_count_1 + 1)
        follow = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), 1)
        self.assertEqual(follow.author, self.user)
        self.assertEqual(follow.user, self.user_follower)

    def test_user_unfollow(self):
        """Авторизованный пользователь может  отписываться
        от других пользователей.
        """
        self.assertEqual(self.user.following.count(), 1)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                args=(self.user.username,)
            )
        )
        self.assertEqual(self.user.following.count(), 0)

    def test_follow(self):
        """
        Новая запись пользователя появляется
        в ленте c подпиской.
        """
        Post.objects.all().delete()
        self.assertEqual(Post.objects.count(), 0)
        new_post = Post.objects.create(
            author=self.user,
            text='Новый пост'
        )
        response = self.authorized_client.get(reverse(
            'posts:follow_index')
        )
        self.assertEqual(
            new_post,
            response.context['page_obj'][0],
        )
        self.assertEqual(len(
            response.context.get('page_obj')), 1
        )
        post = response.context['post']
        self.assertEqual(post.text, new_post.text)
        self.assertEqual(post.author, new_post.author)

    def test_not_follow(self):
        """Новая запись пользователя не появляется
        в ленте без подписки.
        """
        Post.objects.all().delete()
        self.assertEqual(Post.objects.count(), 0)
        new_user = User.objects.create_user(
            username='New_user'
        )
        Post.objects.create(
            author=new_user,
            text='Новый пост'
        )
        response = self.authorized_client.get(reverse(
            'posts:follow_index')
        )
        self.assertEqual(len(
            response.context['page_obj']), 0
        )


class PaginatorTest(TestCase):
    POSTS_PER_PAGE: int = 10

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='User_test')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group_slug = 'user_test_slug'
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug=cls.group_slug,
            description='Тестовое описание',
        )
        post_list = [
            Post(
                author=cls.user,
                text=f'Тестовый пост {number}',
                group=cls.group
            ) for number in range(14)
        ]
        Post.objects.bulk_create(post_list)

    def test_paginator_correct_context_page_one(self):
        """
        Шаблоны index, group_list и profile
        с корректным пагинатором первой страницы
        """
        cache.clear()
        paginator_data = [
            reverse('posts:index'),
            reverse('posts:group_list', args=[self.group.slug]),
            reverse('posts:group_list', args=[self.group.slug]),
        ]
        for requested_page in paginator_data:
            with self.subTest(requested_page=requested_page):
                response = self.authorized_client.get(requested_page)
                self.assertEqual(
                    len(
                        response.context['page_obj']
                    ), self.POSTS_PER_PAGE
                )

    def test_paginator_correct_context_page_two(self):
        """
        Шаблоны index, group_list и profile
        с корректным пагинатором второй страницы
        """
        cache.clear()
        second_page = Post.objects.count() - self.POSTS_PER_PAGE
        paginator_data = [
            reverse('posts:index'),
            reverse('posts:group_list', args=[self.group.slug]),
            reverse('posts:group_list', args=[self.group.slug]),
        ]
        for requested_page in paginator_data:
            with self.subTest(requested_page=requested_page):
                response = self.authorized_client.get(
                    requested_page,
                    {'page': 2},
                )
                self.assertEqual(
                    len(response.context['page_obj']),
                    second_page,
                )
