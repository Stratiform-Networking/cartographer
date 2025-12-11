import { createRouter, createWebHistory } from 'vue-router';
import HomePage from './components/HomePage.vue';
import NetworkView from './components/NetworkView.vue';
import EmbedView from './components/EmbedView.vue';
import AcceptInvite from './components/AcceptInvite.vue';

const routes = [
	{
		path: '/',
		name: 'home',
		component: HomePage
	},
	{
		path: '/network/:id',
		name: 'network',
		component: NetworkView,
		props: true
	},
	{
		path: '/embed/:embedId',
		name: 'embed',
		component: EmbedView,
		props: true
	},
	{
		path: '/accept-invite',
		name: 'accept-invite',
		component: AcceptInvite
	}
];

const router = createRouter({
	history: createWebHistory(),
	routes
});

export default router;
