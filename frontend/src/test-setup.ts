import '@testing-library/jest-dom/vitest'
import { configure } from '@testing-library/react'

// Con varios archivos de prueba en paralelo dentro del contenedor, 1 s a veces no alcanza para que
// termine un pedido simulado; el tiempo de espera de findBy*/waitFor no cambia lo que se comprueba.
configure({ asyncUtilTimeout: 4000 })
