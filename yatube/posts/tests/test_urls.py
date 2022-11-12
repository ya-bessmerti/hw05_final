from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='KiberTest')
        cls.user_not_author = User.objects.create_user(
            username='NotKiberTest'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='testslug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Тестовая запись',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(self.user_not_author)

    def test_guest_urls_access(self):
        """Проверка кодов ответа страниц неавторизованному пользователю."""
        status_codes = {
            reverse('posts:index'): HTTPStatus.OK,
            reverse(
                'posts:group_list',
                args=[PostURLTests.group.slug],
            ): HTTPStatus.OK,
            reverse(
                'posts:profile',
                args=[PostURLTests.user],
            ): HTTPStatus.OK,
            reverse(
                'posts:post_detail',
                args=[PostURLTests.post.pk],
            ): HTTPStatus.OK,
            reverse('posts:post_create'): HTTPStatus.FOUND,
            reverse(
                'posts:post_edit',
                args=[PostURLTests.post.pk],
            ): HTTPStatus.FOUND,
        }
        for address, status_code in status_codes.items():
            with self.subTest(status_code=status_code):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, status_code)

    def test_autorized_urls_access(self):
        """Проверка кодов ответа страниц авторизованному пользователю."""
        status_codes = {
            reverse('posts:index'): HTTPStatus.OK,
            reverse(
                'posts:group_list',
                args=[PostURLTests.group.slug],
            ): HTTPStatus.OK,
            reverse(
                'posts:profile',
                args=[PostURLTests.user],
            ): HTTPStatus.OK,
            reverse(
                'posts:post_detail',
                args=[PostURLTests.post.pk],
            ): HTTPStatus.OK,
            reverse('posts:post_create'): HTTPStatus.OK,
            reverse(
                'posts:post_edit',
                args=[PostURLTests.post.pk],
            ): HTTPStatus.OK,
        }
        for address, status_code in status_codes.items():
            with self.subTest(status_code=status_code):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, status_code)

    def test_list_url_redirect_guest(self):
        """Редирект при попытки редактировать пост не автором."""
        url_names_redirects = {
            reverse(
                'posts:post_edit',
                args=[PostURLTests.post.pk],
            ): f'/auth/login/?next=/posts/{self.post.pk}/edit/'
        }
        for address, redirect_address in url_names_redirects.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, redirect_address)

    def test_page_not_found(self):
        """Несуществующая страница вернёт ошибку 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
